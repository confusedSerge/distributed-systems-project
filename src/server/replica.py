import os
from ipaddress import IPv4Address

from time import sleep
from multiprocessing import Process, Event

from model import Auction, AuctionPeersStore
from communication import (
    Unicast,
    Multicast,
    AuctionMessageData,
    MessageSchema,
    MessageFindReplicaRequest,
    MessageFindReplicaResponse,
    MessageFindReplicaAcknowledgement,
    MessageAuctionInformationResponse,
    MessageAuctionInformationAcknowledgement,
    MessageHeartbeatRequest,
    MessageHeartbeatResponse,
    MessageReelectionAnnouncement,
    MessageElectionRequest,
)

from process import (
    Manager,
    AuctionBidListener,
    AuctionPeersListener,
    AuctionManager,
    ReplicaFinder,
)

from constant import (
    communication as com,
    TIMEOUT_HEARTBEAT,
    TIMEOUT_REPLICATION,
    TIMEOUT_ELECTION,
    REPLICA_AUCTION_POOL_SIZE,
    BUFFER_SIZE,
    SLEEP_TIME,
    MULTICAST_AUCTION_PORT,
    MULTICAST_AUCTION_TTL,
)

from util import create_logger, logger, gen_mid, Timeout


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
        self._auction_peers_listener: AuctionPeersListener = None
        self._auction_bid_listener: AuctionBidListener = None
        self._auction_manager: AuctionManager = None
        self._replica_finder: ReplicaFinder = None

        # Events
        self._reelection: Event = Event()
        self._leader: bool = False
        self._leader_address: tuple[IPv4Address, int] = None

        self._logger.info(f"{self._name}: Initialized")

    def run(self) -> None:
        """Runs the replica background tasks."""
        self._logger.info(f"{self._name}: Started")

        # Initialize shared memory
        self.manager.start()
        self.manager_running.set()
        self._logger.info(f"{self._name}: Started manager")

        self.peers: AuctionPeersStore = self.manager.AuctionPeersStore()

        self._prelude()

        # Check if replica received stop signal during prelude
        if self._exit.is_set():
            self._logger.info(
                f"{self._name}: Replica received stop signal during prelude"
            )
            self._stop_listeners()
            return

        self._logger.info(f"{self._name}: Listeners started")

        # Wait till initial peers are received
        self._logger.info(f"{self._name}: Waiting for initial peers")
        while not self._exit.is_set():
            if self.peers.len() > 0:
                break
            sleep(SLEEP_TIME)
            self._logger.info(
                f"{self._name}: Waiting for initial peers, current: {self.peers.len()}"
            )
        self._logger.info(f"{self._name}: Initial peers received")
        self.auction.next_state()

        # Start replica leader/follower tasks (heartbeat, election, etc.)
        # TODO: impl leader/follower tasks
        self._logger.info(f"{self._name}: Starting leader/follower tasks")

        while not self._exit.is_set():
            # Hold election
            self._logger.info(f"{self._name}: Election")
            self._election()

            # Start listening for reelection announcements
            self._logger.info(f"{self._name}: Starting reelection listener")
            reelection_listener: Process = Process(
                target=self._reelection_listener, name="ReelectionListener"
            )
            reelection_listener.start()

            # Start Leader tasks
            if self._leader:
                self._logger.info(
                    f"{self._name}: Elected leader; Starting auction manager"
                )
                self._auction_manager = AuctionManager(self.auction)
                self._auction_manager.start()

            # Start Heartbeat
            self._heartbeat(self._leader)

        self._logger.info(f"{self._name}: Releasing resources")

        self._stop_listeners()

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

                self._start_listeners()

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

        self._logger.info(f"{self._name}: PRELUDE: Received auction information")

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

    def _start_listeners(self) -> None:
        """Starts the listeners after the auction information is received."""

        # Start listeners
        self._logger.info(f"{self._name}: PRELUDE: Starting listeners")

        self._auction_peers_listener: AuctionPeersListener = AuctionPeersListener(
            self.auction, self.peers
        )
        self._auction_bid_listener: AuctionBidListener = AuctionBidListener(
            self.auction
        )

        self._auction_peers_listener.start()
        self._auction_bid_listener.start()

        self._logger.info(f"{self._name}: PRELUDE: Listeners started")

    def _stop_listeners(self):
        """Stops the listeners."""

        self._logger.info(f"{self._name}: Stopping listeners")

        if self._auction_peers_listener.is_alive():
            self._auction_peers_listener.stop()
            self._auction_peers_listener.join()

        if self._auction_bid_listener.is_alive():
            self._auction_bid_listener.stop()
            self._auction_bid_listener.join()

        self._logger.info(f"{self._name}: Listeners stopped")

    def _election(self) -> None:
        """Handles the election of the replica.

        # TODO: Implement actual election, this is just a placeholder
        """
        self._logger.info(f"{self._name}: ELECTION: Started")

        ticket: MessageElectionRequest = MessageElectionRequest(
            _id=gen_mid(self.auction.get_id()), ticket=os.getpid()
        )

        for replica in self.peers.iter():
            self._logger.info(f"{self._name}: ELECTION: Sending election to {replica}")
            Unicast.qsend(
                message=ticket.encode(),
                host=replica[0],
                port=replica[1],
            )

        self._logger.info(f"{self._name}: ELECTION: Election sent to all replicas")

        self._logger.info(f"{self._name}: ELECTION: Starting election listener")
        try:
            tickets = self._listening_tickets()
        except TimeoutError:
            self._logger.info(f"{self._name}: ELECTION: Timeout; Stopping election")

        self._logger.info(f"{self._name}: ELECTION: Tickets received: {tickets}")
        min_ticket: tuple[int, IPv4Address, int] = min(tickets, key=lambda x: x[0])
        self._logger.info(f"{self._name}: ELECTION: Min ticket: {min_ticket}")

        self._leader = min_ticket[1] == self._unicast.get_host()
        self._leader_address = min_ticket[1:]

        self._logger.info(
            f"{self._name}: ELECTION: Is leader: {self._leader} at {self._leader_address}"
        )

        self._logger.info(f"{self._name}: ELECTION: Stopped")

    def _listening_tickets(self) -> list[tuple[int, IPv4Address, int]]:
        """Listens for tickets from other replicas.

        Returns:
            list[tuple[int, IPv4Address, int]]: The tickets received.
        """

        tickets: list[tuple[int, IPv4Address, int]] = [
            (os.getpid(), self._unicast.get_host(), self._unicast.get_port())
        ]
        return tickets
        self._logger.info(f"{self._name}: ELECTION: Waiting for tickets")

        with Timeout(TIMEOUT_ELECTION, throw_exception=True):
            while not self._exit.is_set() and len(tickets) >= self.peers.len() - 1:
                try:
                    response, address = self._unicast.receive(BUFFER_SIZE)
                except TimeoutError:
                    continue

                self._logger.info(
                    f"{self._name}: ELECTION: Received message from {address}"
                )

                if not MessageSchema.of(com.HEADER_ELECTION_REQ, response):
                    self._logger.info(
                        f"{self._name}: ELECTION: Received message is not an election"
                    )
                    continue

                election: MessageElectionRequest = MessageElectionRequest.decode(
                    response
                )

                if Auction.parse_id(election._id) != self.auction.get_id():
                    self._logger.info(
                        f"{self._name}: ELECTION: Received election {election._id} for another auction {Auction.parse_id(election._id)}"
                    )
                    continue

                self._logger.info(
                    f"{self._name}: ELECTION: Received election {election} from {address}"
                )
                tickets.append((election.ticket, address[0], address[1]))

        self._logger.info(f"{self._name}: ELECTION: Tickets received")
        return tickets

    def _heartbeat(self, leader: bool) -> None:
        """Handles the heartbeat of the replica.

        # TODO: Implement actual heartbeat, this is just a placeholder

        Args:
            leader (bool): Whether the replica is the leader of the auction.
        """
        if leader:
            self._heartbeat_sender()
        else:
            self._heartbeat_listener()

    def _heartbeat_sender(self) -> None:
        """Handles the heartbeat sender of the replica."""
        self._logger.info(f"{self._name}: HEARTBEAT SENDER: Started")
        while not self._reelection.is_set() and not self._exit.is_set():
            unresponsive_peers: list[tuple[IPv4Address, int]] = []
            for replica in self.peers.iter():
                self._heartbeat_emit(replica)

                try:
                    self._heartbeat_listen(replica)
                except TimeoutError:
                    self._logger.info(
                        f"{self._name}: HEARTBEAT SENDER: Timeout; Replica {replica[0]} is unresponsive"
                    )
                    unresponsive_peers.append(replica)
                    break

            self._handle_unresponsive_replicas(unresponsive_peers)

    def _handle_unresponsive_replicas(self, unresponsive_peers):
        for replica in unresponsive_peers:
            self.peers.remove(*replica)

            # Start replica finder in background if unresponsive peers exist
        if (
            len(unresponsive_peers) > 0
            and self.peers.len() <= REPLICA_AUCTION_POOL_SIZE
        ):
            if self._replica_finder is None or not self._replica_finder.is_alive():
                self._logger.info(
                    f"{self._name}: HEARTBEAT SENDER: Starting replica finder"
                )
                self._replica_finder = ReplicaFinder(
                    self.auction, self.peers, TIMEOUT_REPLICATION
                )
            else:
                self._logger.info(
                    f"{self._name}: HEARTBEAT SENDER: Replica finder already running"
                )

    def _heartbeat_listen(self, replica):
        with Timeout(TIMEOUT_HEARTBEAT, throw_exception=True):
            while not self._exit.is_set():
                response, address = self._unicast.receive(BUFFER_SIZE)

                if not MessageSchema.of(com.HEADER_HEARTBEAT_RES, response):
                    continue

                heartbeat: MessageHeartbeatResponse = MessageHeartbeatResponse.decode(
                    response
                )

                if heartbeat._id != self._initial_find_request._id:
                    continue

                if address[0] != replica[0]:
                    self._logger.info(
                        f"{self._name}: HEARTBEAT SENDER: Received heartbeat {heartbeat._id} a different replica {replica[0]}"
                    )
                    continue

                self._logger.info(
                    f"{self._name}: HEARTBEAT SENDER: Received heartbeat {heartbeat._id} from {address}"
                )

                break

    def _heartbeat_emit(self, replica: tuple[IPv4Address, int]) -> None:
        """Emits a heartbeat to all replica peers, except itself."""

        if replica == self._unicast.get_host():
            return

        self._logger.info(
            f"{self._name}: HEARTBEAT EMITTER: Emitting heartbeat to {replica}"
        )
        heartbeat: MessageHeartbeatRequest = MessageHeartbeatRequest(
            _id=gen_mid(self.auction.get_id())
        )

        Unicast.qsend(
            message=heartbeat.encode(),
            host=replica,
            port=self._unicast.get_port(),
        )

        self._logger.info(
            f"{self._name}: HEARTBEAT SENDER: Sent heartbeat {heartbeat._id} to {replica}"
        )

    def _heartbeat_listener(self) -> None:
        """Handles the heartbeat listener of the replica."""
        self._logger.info(f"{self._name}: HEARTBEAT LISTENER: Started")
        while not self._reelection.is_set() and not self._exit.is_set():
            try:
                with Timeout(
                    TIMEOUT_HEARTBEAT * self.peers.len(), throw_exception=True
                ):
                    while not self._exit.is_set():
                        response, address = self._unicast.receive(BUFFER_SIZE)

                        if not MessageSchema.of(com.HEADER_HEARTBEAT_REQ, response):
                            continue

                        heartbeat: MessageHeartbeatRequest = (
                            MessageHeartbeatRequest.decode(response)
                        )

                        if address[0] != self._leader_address[0]:
                            self._logger.info(
                                f"{self._name}: HEARTBEAT LISTENER: Received heartbeat {heartbeat._id} from {address} for another leader {self._leader_address[0]}"
                            )
                            continue

                        self._logger.info(
                            f"{self._name}: HEARTBEAT LISTENER: Received heartbeat {heartbeat._id} from {address}"
                        )

                        heartbeat_response: MessageHeartbeatResponse = (
                            MessageHeartbeatResponse(_id=heartbeat._id)
                        )

                        Unicast.qsend(
                            message=heartbeat_response.encode(),
                            host=self._leader_address[0],
                            port=self._leader_address[1],
                        )

                        break
            except TimeoutError:
                self._logger.info(
                    f"{self._name}: HEARTBEAT LISTENER: Timeout; Starting election"
                )
                self._reelection.set()
                break

    def _reelection_listener(self) -> None:
        mc = Multicast(
            host=self.auction.get_address(),
            port=MULTICAST_AUCTION_PORT,
            ttl=MULTICAST_AUCTION_TTL,
        )

        self._logger.info(f"{self._name}: REELECTION LISTENER: Started")
        while not self._reelection.is_set() and not self._exit.is_set():
            try:
                response, address = mc.receive(BUFFER_SIZE)
            except TimeoutError:
                continue

            if not MessageSchema.of(com.HEADER_REELECTION_ANNOUNCEMENT, response):
                continue

            announcement: MessageReelectionAnnouncement = (
                MessageReelectionAnnouncement.decode(response)
            )

            if Auction.parse_id(announcement._id) != self.auction.get_id():
                self._logger.info(
                    f"{self._name}: REELECTION LISTENER: Received reelection announcement {announcement._id} for another auction {Auction.parse_id(announcement._id)}"
                )
                continue

            self._logger.info(
                f"{self._name}: REELECTION LISTENER: Received reelection announcement {announcement._id} from {address}"
            )

            self._reelection.set()
            break

        self._logger.info(f"{self._name}: REELECTION LISTENER: Stopped")
