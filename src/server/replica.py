from ipaddress import IPv4Address

from time import sleep
from multiprocessing import Process, Event

from model import Auction, AuctionPeersStore
from communication import (
    Multicast,
    Unicast,
    MessageSchema,
    MessageFindReplicaRequest,
    MessageFindReplicaResponse,
    MessageFindReplicaAcknowledgement,
    MessagePeersAnnouncement,
    AuctionMessageData,
    MessageAuctionInformationResponse,
)

from process import Manager, AuctionBidListener, AuctionPeersListener

from constant import (
    header as hdr,
    USERNAME,
    TIMEOUT_REPLICATION,
    BUFFER_SIZE,
    UNICAST_PORT,
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

        # Shared memory
        self.manager: Manager = Manager()
        self.manager_running: Event = Event()

        self.auction: Auction = None
        self.peers: AuctionPeersStore = None

        # Sub processes
        self._auction_peers_listener: Process = None
        self._auction_bid_listener: Process = None

    def run(self) -> None:
        """Runs the replica background tasks."""
        # Initialize shared memory
        self.manager.start()
        self.manager_running.set()

        self._prelude()

        # Check if replica received stop signal during prelude
        if self._exit.is_set():
            self._logger.info("Replica is exiting")
            return

        # Start listeners
        self._auction_peers_listener: AuctionPeersListener = AuctionPeersListener(
            self.auction.get_id(), self.peers
        )
        self._auction_bid_listener: AuctionBidListener = AuctionBidListener(
            self.auction
        )
        self._auction_bid_listener.start()

        # Start replica leader/follower tasks (heartbeat, election, etc.)
        # TODO: impl leader/follower tasks
        while not self._exit.is_set():
            sleep(10)

        # TODO: Stop all possible sub processes (replica finder, auction listener, auction manager etc.)
        self._auction_bid_listener.stop()

    def stop(self) -> None:
        """Stops the replica."""
        self._exit.set()
        self._logger.info("Replica received stop signal")

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
        uc: Unicast = Unicast(host=None, port=UNICAST_PORT)

        # Send join message to auctioneer
        response: MessageFindReplicaResponse = MessageFindReplicaResponse(
            self._initial_find_request._id
        )
        Unicast.qsend(
            message=response.encode(),
            host=self._sender,
            port=UNICAST_PORT,
        )

        # Wait for auctioneer to acknowledge, or timeout
        try:
            self._wait_acknowledge(uc)
        except TimeoutError:
            self._logger.info("Did not receive acknowledgement from auctioneer")
            uc.close()
            self.stop()
            return

        # Wait for auctioneer to send auction information and peers, or timeout
        try:
            self._wait_information(uc)
        except TimeoutError:
            self._logger.info("Did not receive auction information from auctioneer")
            self.stop()
            return
        finally:
            uc.close()

    def _wait_information(self, uc: Unicast) -> None:
        """Waits for the auctioneer to send the state of the auction.

        Args:
            uc (Unicast): The unicast socket.

        Raises:
            TimeoutError: If the auctioneer did not send the state of the auction in time.
        """
        recv_information: bool = False
        recv_peers: bool = False
        with Timeout(TIMEOUT_REPLICATION, throw_exception=True):
            while not self._exit.is_set():
                try:
                    message, address = uc.receive(BUFFER_SIZE)
                except TimeoutError:
                    continue

                if (
                    MessageSchema.of(hdr.AUCTION_INFORMATION_RES, message)
                    and not recv_information
                ):
                    recv_information = self._handle_auction_information_message(
                        message, IPv4Address(address[0])
                    )
                    continue

                if MessageSchema.of(hdr.PEERS_ANNOUNCEMENT, message) and not recv_peers:
                    recv_peers = self._handle_replica_announcement_message(
                        message, IPv4Address(address[0])
                    )
                    continue

                if recv_information and recv_peers:
                    break

    def _wait_acknowledge(self, uc: Unicast) -> None:
        """Waits for the auctioneer to acknowledge the join message.

        Args:
            uc (Unicast): The unicast socket.

        Raises:
            TimeoutError: If the auctioneer did not acknowledge the join message in time.
        """
        with Timeout(TIMEOUT_REPLICATION, throw_exception=True):
            while not self._exit.is_set():
                response, address = uc.receive(BUFFER_SIZE)

                if MessageSchema.of(hdr.FIND_REPLICA_ACKNOWLEDGEMENT, response):
                    continue

                response: MessageFindReplicaAcknowledgement = (
                    MessageFindReplicaAcknowledgement.decode(response)
                )
                if response.auction_id != self._initial_find_request._id:
                    continue

                self._logger.info(f"Received acknowledgement from auctioneer {address}")

                break

    def _handle_auction_information_message(
        self,
        message: MessageAuctionInformationResponse,
        address: IPv4Address,
    ) -> bool:
        """Handles an auction information message.

        Args:
            message (MessageAuctionInformationResponse): The auction information message.

        Returns:
            bool: Whether the message was for this replica.
        """
        message: MessageAuctionInformationResponse = (
            MessageAuctionInformationResponse.decode(message)
        )
        if message._id != self._initial_find_request._id:
            return False

        auction = AuctionMessageData.to_auction(message.auction_information)
        self.auction: Auction = self.manager.Auction(
            auction.get_name(),
            auction.get_auctioneer(),
            auction.get_item(),
            auction.get_price(),
            auction.get_time(),
            auction.get_multicast_address(),
        )
        self.auction.from_other(auction)

        self._logger.info(
            f"Received auction information from {address}: {self.auction}"
        )
        return True

    def _handle_replica_announcement_message(
        self,
        message: MessagePeersAnnouncement,
        address: IPv4Address,
    ) -> bool:
        """Handles a replica announcement message.

        Args:
            message (MessageReplicaAnnouncement): The replica announcement message.

        Returns:
            bool: Whether the message was for this replica.
        """
        replica: MessagePeersAnnouncement = MessagePeersAnnouncement.decode(message)
        if replica._id != self._initial_find_request._id:
            return False

        self.peers: AuctionPeersStore = self.manager.AuctionPeersStore()
        self.peers.replace(replica.peers)
        self._logger.info(f"Received replica announcement from {address}: {self.peers}")
        return True
