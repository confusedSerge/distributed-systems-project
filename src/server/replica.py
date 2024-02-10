from typing import Optional

from ipaddress import IPv4Address

from multiprocessing import Process, Event as ProcessEvent
from multiprocessing.synchronize import Event
from time import sleep, time

from logging import Logger

# === Custom Modules ===

from model import Auction, Leader, AuctionPeersStore
from communication import (
    ReliableUnicast,
    AuctionMessageData,
    MessageSchema,
    MessageFindReplicaRequest,
    MessageFindReplicaResponse,
    MessageAuctionInformationReplication,
    MessageHeartbeatRequest,
    MessageHeartbeatResponse,
    MessageElectionRequest,
    MessageElectionAnswer,
    MessageElectionCoordinator,
)
from process import (
    Manager,
    AuctionManager,
    ReplicationManager,
    AuctionBidListener,
    AuctionPeersAnnouncementListener,
    AuctionStateAnnouncementListener,
    AuctionReelectionListener,
)
from util import create_logger, generate_message_id, Timeout

from constant import (
    communication as com,
    SLEEP_TIME,
    AUCTION_POOL_SIZE,
    COMMUNICATION_BUFFER_SIZE,
    COMMUNICATION_RELIABLE_RETRIES,
    COMMUNICATION_RELIABLE_TIMEOUT,
    REPLICA_HEARTBEAT_PERIOD,
    REPLICA_REPLICATION_PERIOD,
    REPLICA_REPLICATION_TIMEOUT,
    REPLICA_ELECTION_PORTS,
    REPLICA_ELECTION_TIMEOUT,
)


class Replica(Process):
    """Replica class.

    A replica is a server that is responsible for handling a single auction (in combination with other replica peers).
    """

    def __init__(
        self, request: MessageFindReplicaRequest, sender: tuple[IPv4Address, int]
    ) -> None:
        """Initializes the replica class."""
        super(Replica, self).__init__()
        self._exit: Event = ProcessEvent()

        self._name: str = self.__class__.__name__.lower()
        self._prefix: str = f"{self._name}::{request._id}"
        self._logger: Logger = create_logger(self._name, with_pid=True)

        # Initial request and sender information from replica-searcher
        # This is used to send the response and receive the state of the auction in the prelude
        self._initial_sender: tuple[IPv4Address, int] = sender
        self._initial_request: MessageFindReplicaRequest = request

        # Communication
        self._unicast: ReliableUnicast = ReliableUnicast(
            timeout=COMMUNICATION_RELIABLE_TIMEOUT, retry=COMMUNICATION_RELIABLE_RETRIES
        )

        # Shared memory
        self.manager: Manager = Manager()
        self.manager_running: Event = ProcessEvent()

        self.auction: Optional[Auction] = None
        self.peers: Optional[AuctionPeersStore] = None
        self.leader: Optional[Leader] = None

        # Sub processes

        ## Auction Listeners and Managers
        self._auction_bid_listener: Optional[AuctionBidListener] = None
        self._auction_state_listener: Optional[AuctionStateAnnouncementListener] = None
        self._auction_manager: Optional[AuctionManager] = None

        ## Auction Peers Listener and Manager
        self._auction_peers_listener: Optional[AuctionPeersAnnouncementListener] = None
        self._replica_finder: Optional[ReplicationManager] = None
        self.peer_change: Event = ProcessEvent()

        ## Election
        self._reelection_listener: Optional[AuctionReelectionListener] = None
        self.reelection: Event = ProcessEvent()
        self.coordinator: Event = ProcessEvent()

        self._logger.info(f"{self._prefix}: Initialized with id {self.get_id()}")

    def run(self) -> None:
        """Runs the replica process.

        This done through the following steps:
            - Running the prelude (setting up the replica)
            - Waiting for initial peers to be received from peers listener
            - If replica is one of the initial peers, move auction to running state
            - Start replica leader/follower tasks (heartbeat, election, etc.)
            - Wait for auction to end
            - Perform Auction finish tasks
            - Release resources

        """
        self._logger.info(f"{self._prefix}: Started")

        self._init_shared_memory()
        self._prelude()

        # Check if replica received stop signal during prelude
        if self._exit.is_set():
            self._logger.info(
                f"{self._prefix}: Replica received stop signal during prelude"
            )
            self._handle_stop()
            return

        assert self.auction is not None
        assert self.peers is not None

        # Start replica leader/follower tasks (heartbeat, election, etc.)
        self._logger.info(
            f"{self._prefix}: Starting main loop with auction {self.auction} and {self.peers.len()} peers"
        )

        self._logger.info(
            f"{self._prefix}: MAIN LOOP: ELECTION: Triggering election process as new replica"
        )
        self.reelection.set()
        self._election()
        self._main_auction_loop()

        self._logger.info(f"{self._prefix}: END: Releasing resources")

        self._handle_stop()

        self._logger.info(f"{self._prefix}: END: Stopped")

    def stop(self) -> None:
        """Stops the replica."""
        self._exit.set()
        self._logger.info(f"{self._prefix}: Stop signal received")

    def get_id(self) -> tuple[str, int]:
        """Returns the id of the replica consisting of the ip address and port of the replica."""
        return (str(self._unicast.get_address()[0]), self._unicast.get_address()[1])

    # === MAIN AUCTION LOOP ===

    def _main_auction_loop(self):
        """Handles the main auction tasks of the replica."""
        assert self.auction is not None

        self._logger.info(
            f"{self._prefix}: MAIN LOOP: Started for auction {self.auction}"
        )
        while not self._exit.is_set() and not (
            self.auction.is_ended() or self.auction.is_cancelled()
        ):
            # Start Leader tasks
            if self._is_leader():
                self._logger.info(
                    f"{self._prefix}: MAIN LOOP: LEADER: Starting auction manager"
                )
                self._auction_manager = AuctionManager(self.auction)
                self._auction_manager.start()

            self._heartbeat()

            # Stop Leader tasks
            if self._is_leader() and self._auction_manager is not None:
                self._logger.info(
                    f"{self._prefix}: MAIN LOOP: LEADER: Stopping auction manager"
                )
                self._auction_manager.stop()
                self._auction_manager.join()

            if self._replica_finder is not None and self._replica_finder.is_alive():
                self._logger.info(
                    f"{self._prefix}: MAIN LOOP: LEADER: Stopping replica finder"
                )
                self._replica_finder.stop()
                self._replica_finder.join()

            # Start Election
            while self.reelection.is_set():
                self._logger.info(f"{self._prefix}: MAIN LOOP: REELECTION: Started")
                self._election()
                self.reelection.clear()
                self._logger.info(f"{self._prefix}: MAIN LOOP: REELECTION: Stopped")

        # Auction has ended
        self._logger.info(f"{self._prefix}: MAIN LOOP: Auction ended")
        self._logger.info(f"{self._prefix}: MAIN LOOP: Stopped")

    # === PRELUDE ===

    def _prelude(self) -> None:
        """Handles the prelude of the replica.

        This initializes the replica to be ready to handle the auction either as a leader or follower.

        This is done through the following steps:
            - Responding to the replica-searcher replica request to indicate that the replica is available.
            - Waiting for the auctioneer to send the state of the auction.
            - Starting the listeners.

        If the replica does not receive confirmation from the replica-searcher or the auction in time, the replica will set the stop signal.
        """
        self._logger.info(f"{self._prefix}: PRELUDE: Started")

        # Send response to auctioneer
        try:
            self._unicast.send(
                MessageFindReplicaResponse(_id=self._initial_request._id).encode(),
                self._initial_sender,
            )
        except TimeoutError:
            self._logger.info(
                f"{self._prefix}: PRELUDE: Sender not reachable; Response not sent. Exiting"
            )
            self.stop()
            return

        self._logger.info(
            f"{self._prefix}: PRELUDE: Replica response sent to {self._initial_sender}"
        )

        # Wait for auctioneer to send auction information, or timeout
        self._logger.info(f"{self._prefix}: PRELUDE: Waiting for auction information")
        if not self._wait_information():
            self._logger.info(
                f"{self._prefix}: PRELUDE: Auction information not received; Exiting"
            )
            self.stop()
            return

        # Finalize prelude
        self._finalize_prelude()

        self._logger.info(f"{self._prefix}: PRELUDE: Prelude concluded")

    def _wait_information(self) -> bool:
        """Waits for the auctioneer to send the state of the auction.

        Raises:
            TimeoutError: If the auctioneer did not send the state of the auction in time.
        """
        self._logger.info(f"{self._prefix}: PRELUDE: Waiting for auction information")

        end_time = time() + REPLICA_REPLICATION_TIMEOUT

        while not self._exit.is_set() and time() <= end_time:
            try:
                message, address = self._unicast.receive(COMMUNICATION_BUFFER_SIZE)
            except TimeoutError:
                continue

            if (
                not MessageSchema.of(
                    com.HEADER_AUCTION_INFORMATION_REPLICATION, message
                )
                or MessageSchema.get_id(message) != self._initial_request._id
                or address != self._initial_sender
            ):
                continue

            response: MessageAuctionInformationReplication = (
                MessageAuctionInformationReplication.decode(message)
            )

            self._handle_auction_information_message(response)

            self._logger.info(
                f"{self._prefix}: PRELUDE: Auction information received: {self.auction}"
            )
            return True

        return False

    def _finalize_prelude(self) -> None:
        """Finalizes the prelude by starting the listeners and
        sending an acknowledgement to the replica searcher
        to indicate that the replica is ready to handle the auction.
        """
        self._logger.info(f"{self._prefix}: PRELUDE: Finalizing prelude")

        self._start_listeners()

        assert self.auction is not None
        assert self.peers is not None

        # Wait till initial peers are received
        self._logger.info(f"{self._prefix}: PEERS: Waiting for initial peers")
        end_time = time() + REPLICA_REPLICATION_TIMEOUT
        while (
            not self._exit.is_set()
            and not self.peer_change.is_set()
            and time() <= end_time
        ):
            sleep(SLEEP_TIME)

        if not self.peer_change.is_set():
            self._logger.info(f"{self._prefix}: PEERS: Peers not received; Exiting")
            self.stop()
            return

        if self._exit.is_set():
            self._logger.info(
                f"{self._prefix}: PEERS: Replica received stop signal during peer wait"
            )
            self._handle_stop()
            return

        assert self.peers.len() > 0, "No peers received, yet process event was set"
        self.peer_change.clear()
        sleep(SLEEP_TIME)
        self._logger.info(
            f"{self._prefix}: PEERS: Initial peers received: {[peer for peer in self.peers.iter()]}"
        )

        self._logger.info(f"{self._prefix}: PRELUDE: Prelude finalized")

    # === HEARTBEAT ===

    def _heartbeat(self) -> None:
        """Handles the heartbeat of the replica."""
        if self._is_leader():
            self._heartbeat_sender()
        else:
            self._heartbeat_listener()

    def _heartbeat_sender(self) -> None:
        """Handles the heartbeat emission of heartbeats and removal of unresponsive replicas."""
        assert self.auction is not None
        assert self.peers is not None

        self._logger.info(f"{self._prefix}: HEARTBEAT SENDER: Started")

        while not self.reelection.is_set() and not self._exit.is_set():
            # Create peers dict for keeping track of unresponsive peers
            responses: dict[tuple[IPv4Address, int], bool] = {
                replica: False
                for replica in self.peers.iter()
                if replica != self._unicast.get_address()
            }

            # Emit heartbeat and listen for responses
            heartbeat_id: str = self._heartbeat_emit(responses)
            self._heartbeat_response_listener(heartbeat_id, responses)

            # Check if peer change or exit signal was set during heartbeat
            if self.reelection.is_set() or self._exit.is_set():
                break

            # Handle unresponsive peers
            unresponsive_peers: list[tuple[IPv4Address, int]] = [
                replica for replica, responded in responses.items() if not responded
            ]
            if len(unresponsive_peers) > 0:
                self._logger.info(
                    f"{self._prefix}: HEARTBEAT SENDER: Unresponsive peers: {unresponsive_peers}"
                )
                self._handle_unresponsive_replicas(unresponsive_peers)

            self._logger.info(
                f"{self._prefix}: HEARTBEAT SENDER: Sleeping one heartbeat period {REPLICA_HEARTBEAT_PERIOD}s before next heartbeat"
            )
            sleep(REPLICA_HEARTBEAT_PERIOD)

        self._logger.info(f"{self._prefix}: HEARTBEAT SENDER: Stopped")

    def _heartbeat_emit(self, replicas: dict[tuple[IPv4Address, int], bool]) -> str:
        """Emits a heartbeat to all replica peers in the dict.
        If a replica responds, the value of the replica is set to True.

        Args:
            replicas (dict[tuple[IPv4Address, int], bool]): The replicas to emit a heartbeat to.

        Returns:
            str: The id of the heartbeat.
        """
        assert self.auction is not None

        heartbeat_id = generate_message_id(self.auction.get_id())
        heartbeat: bytes = MessageHeartbeatRequest(_id=heartbeat_id).encode()

        self._logger.info(
            f"{self._prefix}: HEARTBEAT SENDER: Emitting heartbeats with id {heartbeat_id}"
        )
        for replica in replicas.keys():
            self._unicast.usend(heartbeat, replica)
            self._logger.info(
                f"{self._prefix}: HEARTBEAT SENDER: Sent heartbeat {heartbeat_id} to {replica}"
            )

        self._logger.info(f"{self._prefix}: HEARTBEAT SENDER: Heartbeats emitted")

        return heartbeat_id

    def _heartbeat_response_listener(
        self, heartbeat_id: str, replicas: dict[tuple[IPv4Address, int], bool]
    ) -> None:
        """Listens for a heartbeat response from the replicas.

        Args:
            heartbeat_id (str): The id of the heartbeat.
            replicas (dict[tuple[IPv4Address, int], bool]): The replicas to listen for a heartbeat response from.
        """
        self._logger.info(
            f"{self._prefix}: HEARTBEAT SENDER: Listening for heartbeat responses from {replicas.keys()}"
        )

        end_time = time() + REPLICA_HEARTBEAT_PERIOD
        while (
            not self.reelection.is_set()
            and not self._exit.is_set()
            and not all(replicas.values())
            and time() <= end_time
        ):
            try:
                response, address = self._unicast.ureceive(COMMUNICATION_BUFFER_SIZE)
            except TimeoutError:
                continue

            if not MessageSchema.of(com.HEADER_HEARTBEAT_RES, response):
                continue

            heartbeat_response: MessageHeartbeatResponse = (
                MessageHeartbeatResponse.decode(response)
            )

            if heartbeat_response._id != heartbeat_id:
                self._logger.info(
                    f"{self._prefix}: HEARTBEAT SENDER: Received heartbeat {heartbeat_response._id} for another heartbeat {heartbeat_id}"
                )
                continue

            if address not in replicas.keys():
                self._logger.error(
                    f"{self._prefix}: HEARTBEAT SENDER: Received heartbeat from unknown replica {address}"
                )
                continue

            self._logger.info(
                f"{self._prefix}: HEARTBEAT SENDER: Received heartbeat {heartbeat_response._id} from {address}"
            )
            replicas[address] = True

    def _heartbeat_listener(self) -> None:
        """Handles the heartbeat listener of the replica.

        If the replica does not receive a heartbeat from the leader in time, the replica will set the reelection signal.
        """
        assert self.leader is not None
        assert self.peers is not None

        self._logger.info(f"{self._prefix}: HEARTBEAT LISTENER: Started")
        while not self.reelection.is_set() and not self._exit.is_set():
            end_time = time() + REPLICA_HEARTBEAT_PERIOD

            while (
                not self.reelection.is_set()
                and not self._exit.is_set()
                and time() <= end_time
            ):
                try:
                    response, address = self._unicast.ureceive(
                        COMMUNICATION_BUFFER_SIZE
                    )
                except TimeoutError:
                    continue

                if (
                    not MessageSchema.of(com.HEADER_HEARTBEAT_REQ, response)
                    or address != self.leader
                ):
                    continue

                heartbeat: MessageHeartbeatRequest = MessageHeartbeatRequest.decode(
                    response
                )
                # For heartbeats, it is enough to just respond without reliability
                self._unicast.usend(
                    MessageHeartbeatResponse(_id=heartbeat._id).encode(),
                    self.leader.get(),
                )

                self._logger.info(
                    f"{self._prefix}: HEARTBEAT LISTENER: Received heartbeat {heartbeat._id} from {address}; Responded"
                )

                self._logger.info(
                    f"{self._prefix}: HEARTBEAT LISTENER: Sleeping one heartbeat period {REPLICA_HEARTBEAT_PERIOD}s before next heartbeat"
                )

                sleep(REPLICA_HEARTBEAT_PERIOD)
                end_time = time() + REPLICA_HEARTBEAT_PERIOD

            if self.reelection.is_set() or self._exit.is_set():
                return

            self._logger.info(
                f"{self._prefix}: HEARTBEAT LISTENER: Timeout; Starting election"
            )
            # Remove leader from peers
            self.peers.remove(*self.leader.get())

            # Initiate reelection if leader is not responding
            self.reelection.set()
            break

    # === HANDLERS ===

    def _handle_unresponsive_replicas(
        self, unresponsive_peers: list[tuple[IPv4Address, int]]
    ) -> None:
        """Handles unresponsive replicas by removing them from the peers list and starting a replica finder if necessary.

        Args:
            unresponsive_peers (list[tuple[IPv4Address, int]]): The unresponsive replicas.
        """
        assert self.peers is not None
        assert self.auction is not None

        self._logger.info(
            f"{self._prefix}: HEARTBEAT SENDER: Handling unresponsive peers"
        )

        for replica in unresponsive_peers:
            self.peers.remove(*replica)

        # Start replica finder in background if there are not enough replicas
        if self.peers.len() <= AUCTION_POOL_SIZE:
            if self._replica_finder is None or not self._replica_finder.is_alive():
                self._logger.info(
                    f"{self._prefix}: HEARTBEAT SENDER: Starting replica finder"
                )
                self._replica_finder = ReplicationManager(
                    self.auction, self.peers, REPLICA_REPLICATION_PERIOD
                )
            else:
                self._logger.info(
                    f"{self._prefix}: HEARTBEAT SENDER: Replica finder already running"
                )

        self._logger.info(
            f"{self._prefix}: HEARTBEAT SENDER: Unresponsive peers handled"
        )

    def _handle_auction_information_message(
        self,
        message: MessageAuctionInformationReplication,
    ):
        """Handles an auction information message by setting the local auction.

        Args:
            message (MessageAuctionInformationResponse): The auction information message.
        """
        assert message._id == self._initial_request._id
        assert self.manager_running.is_set()

        rcv_auction: Auction = AuctionMessageData.to_auction(message.auction)
        self.auction: Optional[Auction] = self.manager.Auction(  # type: ignore
            rcv_auction.get_name(),
            rcv_auction.get_auctioneer(),
            rcv_auction.get_item(),
            rcv_auction.get_price(),
            rcv_auction.get_end_time(),
            rcv_auction.get_group(),
        )

        assert self.auction is not None
        self.auction.from_other(rcv_auction)

    def _handle_stop(self) -> None:
        """Handles the stopping of the replica."""
        self._logger.info(f"{self._prefix}: Stopping replica")

        self._unicast.close()
        self._stop_listeners()

        self.manager_running.clear()
        self.manager.shutdown()

    # === HELPERS ===

    def _init_shared_memory(self):
        """Initializes the shared memory."""
        self._logger.info(f"{self._prefix}: Initializing shared memory")
        self.manager.start()
        self.manager_running.set()
        self._logger.info(f"{self._prefix}: Started manager")

        self.leader: Optional[Leader] = self.manager.Leader(*self._unicast.get_address())  # type: ignore
        self.peers: Optional[AuctionPeersStore] = self.manager.AuctionPeersStore()  # type: ignore
        # Add self to peers or else the shared memory will be garbage collected, as the list is empty :(
        # This has been my worst bug so far
        assert (
            self.peers is not None
        ), "Peers is None after init from memory manager. This case should not be possible"
        self.peers.add(IPv4Address("0.0.0.0"), self._unicast.get_address()[1])

    def _start_listeners(self) -> None:
        """Starts the listeners after the auction information is received."""
        # Asserts
        assert self.auction is not None
        assert self.peers is not None
        assert self.leader is not None

        # Start listeners
        self._logger.info(f"{self._prefix}: PRELUDE: Starting listeners")

        # Auction Listeners
        self._auction_state_listener: Optional[AuctionStateAnnouncementListener] = (
            AuctionStateAnnouncementListener(self.auction)
        )
        self._auction_peers_listener: Optional[AuctionPeersAnnouncementListener] = (
            AuctionPeersAnnouncementListener(self.auction, self.peers, self.peer_change)
        )
        self._auction_bid_listener: Optional[AuctionBidListener] = AuctionBidListener(
            self.auction
        )

        # Election Listener
        self._reelection_listener: Optional[AuctionReelectionListener] = (
            AuctionReelectionListener(
                self.get_id(),
                self.leader,
                self.reelection,
                self.coordinator,
                self.auction.get_id(),
            )
        )

        # Start listeners
        self._auction_state_listener.start()
        self._auction_peers_listener.start()
        self._auction_bid_listener.start()
        self._reelection_listener.start()

        self._logger.info(f"{self._prefix}: PRELUDE: Listeners started")

    def _stop_listeners(self):
        """Stops the listeners."""

        self._logger.info(f"{self._prefix}: Stopping listeners")

        if (
            self._auction_state_listener is not None
            and self._auction_state_listener.is_alive()
        ):
            self._auction_state_listener.stop()
            self._auction_state_listener.join()

        if (
            self._auction_peers_listener is not None
            and self._auction_peers_listener.is_alive()
        ):
            self._auction_peers_listener.stop()
            self._auction_peers_listener.join()

        if (
            self._auction_bid_listener is not None
            and self._auction_bid_listener.is_alive()
        ):
            self._auction_bid_listener.stop()
            self._auction_bid_listener.join()

        if (
            self._reelection_listener is not None
            and self._reelection_listener.is_alive()
        ):
            self._reelection_listener.stop()
            self._reelection_listener.join()

        self._logger.info(f"{self._prefix}: Listeners stopped")

    def _is_leader(self) -> bool:
        """Returns True if the replica is the leader."""
        assert self.leader is not None
        return self.leader.get() == self._unicast.get_address()

    # === ELECTION ===

    def _election(self) -> None:
        """Handles the election of the replica via bully algorithm.

        The election is triggered either by the reelection signal or by the absence of a heartbeat from the leader.
        """
        if self.auction is None or self.peers is None or self.leader is None:
            self._logger.error(
                f"{self._prefix}: ELECTION: Auction, peers or leader is None"
            )
            exit(1)

        if not self.reelection.is_set():
            self._logger.error(
                f"{self._prefix}: ELECTION: Received election signal without reelection signal set"
            )
            return

        if (
            self._reelection_listener is None
            or not self._reelection_listener.is_alive()
        ):
            self._logger.error(
                f"{self._prefix}: ELECTION: Reelection listener is None or not alive"
            )
            exit(1)

        self._logger.info(f"{self._prefix}: ELECTION: Started")

        # Get the id of this replica
        # Check if there's any replica with higher priority
        my_priority: tuple[IPv4Address, int] = self._unicast.get_address()
        higher_priority_replicas = [
            replica for replica in self.peers.iter() if replica > my_priority
        ]

        if not higher_priority_replicas:
            self._logger.info(f"{self._prefix}: ELECTION: No higher priority replicas")

            # Need to wait for replicas to catch up, as best branch to quick, if others need to reliably send to all possible ports
            sleep_time = time() + COMMUNICATION_RELIABLE_RETRIES * len(
                REPLICA_ELECTION_PORTS
            )
            self._send_election_coordinator()
            sleep(sleep_time - time())

            self.leader.set(*self._unicast.get_address())
            self.coordinator.set()
            self.reelection.clear()
            return

        self._logger.info(
            f"{self._prefix}: ELECTION: Detected higher priority replicas, initiating election"
        )
        message_id: str = self._send_election_request(higher_priority_replicas)

        # wait for responses
        if not self._wait_election_responses(message_id):
            self._logger.info(
                f"{self._prefix}: ELECTION: Won the election, broadcasting victory"
            )
            self._send_election_coordinator()

            self.leader.set(*self._unicast.get_address())
            self.coordinator.set()
            self.reelection.clear()
            return

        self._logger.info(
            f"{self._prefix}: ELECTION: Received responses from higher priority replicas"
        )

        # wait for coordinator message from higher priority replica
        try:
            self._wait_coordinator_message()
        except TimeoutError:
            self._logger.info(
                f"{self._prefix}: ELECTION: No victory message received, re-starting election"
            )

            self.coordinator.clear()
            self.reelection.set()

            return

        self._logger.info(
            f"{self._prefix}: ELECTION: Received coordinator message, stopping election"
        )

        self.reelection.clear()
        self.coordinator.clear()

        self._logger.info(f"{self._prefix}: ELECTION: Stopped")

    def _send_election_coordinator(self) -> None:
        """Sends a coordinator message to all replicas."""
        assert self.auction is not None
        assert self.peers is not None

        coordinator_message = MessageElectionCoordinator(
            _id=generate_message_id(self.auction.get_id()), req_id=self.get_id()
        )
        for replica in self.peers.iter():
            if replica == self._unicast.get_address():
                continue
            _received = self._unicast.send_to_all(
                message=coordinator_message.encode(),
                addresses=[(replica[0], port) for port in REPLICA_ELECTION_PORTS],
            )
            self._logger.info(
                f"{self._prefix}: ELECTION: Sent coordinator message to {replica} with port set {REPLICA_ELECTION_PORTS} where {_received} received"
            )

    def _send_election_request(
        self, higher_priority_replicas: list[tuple[IPv4Address, int]]
    ) -> str:
        """Sends an election request to the higher priority replicas.

        Args:
            higher_priority_replicas (list[tuple[IPv4Address, int]]): The higher priority replicas.

        Returns:
            str: The id of the election message.
        """
        assert self.auction is not None

        message_id = generate_message_id(self.auction.get_id())
        election_message = MessageElectionRequest(_id=message_id, req_id=self.get_id())
        for replica in higher_priority_replicas:
            _received = self._unicast.send_to_all(
                message=election_message.encode(),
                addresses=[(replica[0], port) for port in REPLICA_ELECTION_PORTS],
            )
            self._logger.info(
                f"{self._prefix}: ELECTION: Sent election request to {replica} with port set {REPLICA_ELECTION_PORTS} where {_received} received"
            )

        return message_id

    def _wait_election_responses(self, message_id: str) -> bool:
        """Waits for election responses from the higher priority replicas.

        Returns:
            bool: True if an answer was received from a higher priority replica, False otherwise.
        """
        self._logger.info(
            f"{self._prefix}: ELECTION: Waiting for election responses from higher priority replicas"
        )
        end_time = time() + REPLICA_ELECTION_TIMEOUT
        while not self._exit.is_set() and time() <= end_time:
            try:
                response, address = self._unicast.receive(COMMUNICATION_BUFFER_SIZE)
            except TimeoutError:
                continue

            if (
                not MessageSchema.of(com.HEADER_ELECTION_ANS, response)
                or MessageSchema.get_id(response) != message_id
            ):
                self._logger.info(
                    f"{self._prefix}: ELECTION: Received election answer from unknown replica {address} (Ignoring): {response}"
                )
                continue

            answer: MessageElectionAnswer = MessageElectionAnswer.decode(response)

            if answer.req_id < self.get_id():
                f"{self._prefix}: ELECTION: Received election answer from {address} with higher id ({self.get_id()}, (Ignoring)): {answer}"
                continue

            self._logger.info(
                f"{self._prefix}: ELECTION: Received election answer from {address} with higher id ({self.get_id()}, (Stopping)): {answer}"
            )

            return True

        return False

    def _wait_coordinator_message(self) -> None:
        """Waits for a coordinator message from the higher priority replica.

        Raises:
            TimeoutError: raised if no coordinator message is received from the higher priority replica.
        """
        self._logger.info(f"{self._prefix}: ELECTION: Waiting for coordinator message")
        self.coordinator.wait(REPLICA_ELECTION_TIMEOUT)
        if not self.coordinator.is_set():
            raise TimeoutError
        self.coordinator.clear()
