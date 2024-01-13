from ipaddress import IPv4Address

from time import sleep
from multiprocessing import Process, Event

from model import Auction, AuctionPeersStore
from communication import (
    Unicast,
    AuctionMessageData,
    MessageSchema,
    MessageFindReplicaRequest,
    MessageFindReplicaResponse,
    MessageFindReplicaAcknowledgement,
    MessageAuctionInformationResponse,
    MessageAuctionInformationAcknowledgement,
)

from process import Manager, AuctionBidListener, AuctionPeersListener

from constant import (
    communication as com,
    TIMEOUT_REPLICATION,
    BUFFER_SIZE,
    SLEEP_TIME,
)

from util import create_logger, logger, Timeout


class Replica(Process):
    """Replica class.

    A replica is a server that is responsible for handling a single auction (in combination with other replica peers).

    A replica can be described by the following state machine:
        - Joining: The replica is joining the auction multicast group and sending a join message to the auctioneer.
        - Ready: The replica has received its peers and state of auction.
        - Timeout: The replica has did not receive its peers and state of auction in time.

        - Leader Election -> Leader: The replica is the leader of the auction.
        - Leader Election -> Follower: The replica is a follower of the auction.

        - Leader: Handles monitoring of replica peers (heartbeats), finding replicas and "auctioning" (answering incoming requests).
        - Follower: Answers heartbeat messages from the leader and starts a new election if the leader is not responding.

        - Leader and Follower: Background listener of auction.

        - Auction finished: Send winner and stop replica.
    """

    def __init__(self, request: MessageFindReplicaRequest, sender: IPv4Address) -> None:
        """Initializes the replica class."""
        super(Replica, self).__init__()
        self._exit: Event = Event()

        self._name: str = f"Replica::{request._id}"
        self._logger: logger = create_logger(self._name.lower())

        self._initial_find_request: MessageFindReplicaRequest = request
        self._sender: IPv4Address = sender

        # Communication
        self._unicast: Unicast = Unicast(host=None, port=None)

        # Shared memory
        self.manager: Manager = Manager()
        self.manager_running: Event = Event()

        self.auction: Auction = None
        self.peers: AuctionPeersStore = None

        # Sub processes
        self._auction_peers_listener: Process = None
        self._auction_bid_listener: Process = None

        self._logger.info(f"{self._name}: Initialized")

    def run(self) -> None:
        """Runs the replica background tasks."""
        self._logger.info(f"{self._name}: Started")

        # Initialize shared memory
        self.manager.start()
        self.manager_running.set()
        self.logger.info(f"{self._name}: Started manager")

        self._prelude()

        # Check if replica received stop signal during prelude
        if self._exit.is_set():
            self._logger.info(
                f"{self._name}: Replica received stop signal during prelude"
            )
            return

        # Start listeners
        self._logger.info(f"{self._name}: Starting listeners")

        self._auction_peers_listener: AuctionPeersListener = AuctionPeersListener(
            self.auction, self.peers
        )
        self._auction_bid_listener: AuctionBidListener = AuctionBidListener(
            self.auction
        )
        self._auction_peers_listener.start()
        self._auction_bid_listener.start()

        self._logger.info(f"{self._name}: Listeners started")

        # Wait till initial peers are received
        self._logger.info(f"{self._name}: Waiting for initial peers")
        while not self._exit.is_set():
            if len(self.peers) > 0:
                break
            sleep(SLEEP_TIME)
        self._logger.info(f"{self._name}: Initial peers received")
        self.auction.next_state()

        # Start replica leader/follower tasks (heartbeat, election, etc.)
        # TODO: impl leader/follower tasks
        self._logger.info(f"{self._name}: Starting leader/follower tasks")
        while not self._exit.is_set():
            self._logger.info(
                f"{self._name}: Replica will be doing leader/follower tasks"
            )
            sleep(10)

        self._logger.info(f"{self._name}: Releasing resources")

        if self._auction_peers_listener.is_alive():
            self._auction_peers_listener.stop()
            self._auction_peers_listener.join()

        if self._auction_bid_listener.is_alive():
            self._auction_bid_listener.stop()
            self._auction_bid_listener.join()

        self.manager_running.clear()
        self.manager.shutdown()

        self._logger.info(f"{self._name}: Stopped")

    def stop(self) -> None:
        """Stops the replica."""
        self._exit.set()
        self._logger.info(f"{self._name}: Stop signal received")

    def get_id(self) -> str:
        """Returns the id of the replica."""
        return self._initial_find_request._id

    def _prelude(self) -> None:
        """Handles the prelude of the replica.

        This includes:
            - Joining the auction multicast group.
            - Sending a join message to the auctioneer.
            - Waiting for the auctioneer to send the state of the auction.
            - On timeout, leave the auction multicast group and stop the replica.
        """
        self._logger.info(f"{self._name}: PRELUDE: Started")

        # Send join message to auctioneer
        response: MessageFindReplicaResponse = MessageFindReplicaResponse(
            _id=self._initial_find_request._id, port=self._unicast.get_port()
        )
        Unicast.qsend(
            message=response.encode(),
            host=self._sender,
            port=self._initial_find_request.port,
        )
        self._logger.info(
            f"{self._name}: PRELUDE: Replica response sent to ({self._sender}, {self._initial_find_request.port})"
        )

        # Wait for auctioneer to acknowledge, or timeout
        self._logger.info(f"{self._name}: PRELUDE: Waiting for acknowledgement")
        try:
            self._wait_acknowledge()
        except TimeoutError:
            self._logger.info(
                f"{self._name}: PRELUDE: Acknowledgement not received; Exiting"
            )
            self._unicast.close()
            self.stop()
            return
        self._logger.info(f"{self._name}: PRELUDE: Acknowledgement received")

        # Wait for auctioneer to send auction information and peers, or timeout
        self._logger.info(f"{self._name}: PRELUDE: Waiting for auction information")
        try:
            self._wait_information()
        except TimeoutError:
            self._logger.info(
                f"{self._name}: PRELUDE: Auction information not received; Exiting"
            )
            self.stop()
            return
        finally:
            self._unicast.close()

        self._logger.info(
            f"{self._name}: PRELUDE: Auction information received; Prelude concluded"
        )

    def _wait_acknowledge(self) -> None:
        """Waits for the auctioneer to acknowledge the join message.

        Raises:
            TimeoutError: If the auctioneer did not acknowledge the join message in time.
        """
        with Timeout(TIMEOUT_REPLICATION, throw_exception=True):
            while not self._exit.is_set():
                response, _ = self._unicast.receive(BUFFER_SIZE)

                if not MessageSchema.of(com.HEADER_FIND_REPLICA_ACK, response):
                    continue

                response: MessageFindReplicaAcknowledgement = (
                    MessageFindReplicaAcknowledgement.decode(response)
                )
                if response._id != self._initial_find_request._id:
                    continue

                break

    def _wait_information(self) -> None:
        """Waits for the auctioneer to send the state of the auction.

        Raises:
            TimeoutError: If the auctioneer did not send the state of the auction in time.
        """
        with Timeout(TIMEOUT_REPLICATION, throw_exception=True):
            while not self._exit.is_set():
                try:
                    response, address = self._unicast.receive(BUFFER_SIZE)
                except TimeoutError:
                    continue

                if not MessageSchema.of(com.HEADER_AUCTION_INFORMATION_RES, response):
                    continue

                response: MessageAuctionInformationResponse = (
                    MessageAuctionInformationResponse.decode(response)
                )

                self._handle_auction_information_message(response)
                self._logger.info(
                    f"{self._name}: PRELUDE: Auction information received: {self.auction}"
                )

                acknowledgement: MessageAuctionInformationAcknowledgement = (
                    MessageAuctionInformationAcknowledgement(
                        _id=self._initial_find_request._id
                    )
                )

                Unicast.qsend(
                    message=acknowledgement.encode(),
                    host=address[0],
                    port=response.port,
                )
                self._logger.info(
                    f"{self._name}: PRELUDE: Auction information acknowledgement sent ({address[0]}, {response.port})"
                )

                break

        self._logger.info("Received auction information and peers from auctioneer")

    def _handle_auction_information_message(
        self,
        message: MessageAuctionInformationResponse,
    ) -> bool:
        """Handles an auction information message.

        Args:
            message (MessageAuctionInformationResponse): The auction information message.

        Returns:
            bool: Whether the message was for this replica.
        """
        if message._id != self._initial_find_request._id:
            return False

        auction = AuctionMessageData.to_auction(message.auction)
        self.auction: Auction = self.manager.Auction(
            auction.get_name(),
            auction.get_auctioneer(),
            auction.get_item(),
            auction.get_price(),
            auction.get_time(),
            auction.get_address(),
        )
        self.auction.from_other(auction)
        return True
