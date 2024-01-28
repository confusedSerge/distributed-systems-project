from typing import Optional

import os

from ipaddress import IPv4Address

from multiprocessing import Process, Event as ProcessEvent
from multiprocessing.synchronize import Event
from time import sleep

from logging import Logger

# === Custom Modules ===

from model import Auction, AuctionPeersStore
from communication import (
    Unicast,
    AuctionMessageData,
    MessageSchema,
    MessageFindReplicaRequest,
    MessageFindReplicaResponse,
    MessageAuctionInformationResponse,
    MessageAuctionInformationAcknowledgement,
    MessageHeartbeatRequest,
    MessageHeartbeatResponse,
)
from process import (
    Manager,
    AuctionBidListener,
    AuctionPeersAnnouncementListener,
    AuctionManager,
    ReplicaFinder,
)
from util import create_logger, generate_message_id, Timeout

from constant import (
    communication as com,
    TIMEOUT_HEARTBEAT,
    REPLICA_EMITTER_PERIOD,
    TIMEOUT_REPLICATION,
    TIMEOUT_RECEIVE,
    REPLICA_AUCTION_POOL_SIZE,
    BUFFER_SIZE,
    SLEEP_TIME,
)


class Replica(Process):
    """Replica class.

    A replica is a server that is responsible for handling a single auction (in combination with other replica peers).

    TODO:
        - Implement actual election
        - Auction Management
    """

    def __init__(
        self, request: MessageFindReplicaRequest, sender: tuple[IPv4Address, int]
    ) -> None:
        """Initializes the replica class."""
        super(Replica, self).__init__()
        self._exit: Event = ProcessEvent()

        self._name: str = f"Replica::{request._id}"
        self._logger: Logger = create_logger(self._name.lower())

        # Initial request and sender information from replica-searcher
        # This is used to send the response and receive the state of the auction in the prelude
        self._initial_sender: tuple[IPv4Address, int] = sender
        self._initial_request: MessageFindReplicaRequest = request

        # Communication
        self._unicast: Unicast = Unicast(timeout=TIMEOUT_RECEIVE)

        # Shared memory
        self.manager: Manager = Manager()
        self.manager_running: Event = ProcessEvent()

        self.auction: Optional[Auction] = None
        self.peers: Optional[AuctionPeersStore] = None
        self.peer_change: Event = ProcessEvent()

        # Sub processes
        self._auction_peers_listener: Optional[AuctionPeersAnnouncementListener] = None
        self._auction_bid_listener: Optional[AuctionBidListener] = None
        self._auction_manager: Optional[AuctionManager] = None
        self._replica_finder: Optional[ReplicaFinder] = None
        self._reelection_listener: Optional[Process] = None

        # Leader
        self._leader: tuple[IPv4Address, int] = self._unicast.get_address()
        self._is_leader: bool = False

        self.reelection: Event = ProcessEvent()

        self._logger.info(f"{self._name}: Initialized")

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

        TODO:
            - Implement actual election
            - Auction Management
            - Auction Finish tasks

        """
        self._logger.info(f"{self._name}: Started")

        self._init_shared_memory()
        self._prelude()

        # Check if replica received stop signal during prelude
        if self._exit.is_set():
            self._logger.info(
                f"{self._name}: Replica received stop signal during prelude"
            )
            self._handle_stop()
            return

        # Check that prelude was successful
        assert self.auction is not None
        assert self.peers is not None

        # Wait till initial peers are received
        self._logger.info(f"{self._name}: Waiting for peers")
        while not self._exit.is_set() and self.peer_change.is_set():
            sleep(SLEEP_TIME)

        assert self.peers.len() > 0, "No peers received, yet process event was set"
        self.peer_change.clear()
        self._logger.info(f"{self._name}: Initial peers received")

        # Check if replica is one of the initial peers and move auction to running state
        if self.auction.is_preparation():
            self._logger.info(f"{self._name}: Auction is in preparation state")
            self.auction.next_state()
            self._logger.info(f"{self._name}: Auction set to running state")

        # Start replica leader/follower tasks (heartbeat, election, etc.)
        self._logger.info(
            f"{self._name}: Starting leader/follower tasks with auction {self.auction} and {self.peers.len()} peers"
        )

        self._main_auction_loop()

        self._logger.info(f"{self._name}: Releasing resources")

        self._handle_stop()

        self._logger.info(f"{self._name}: Stopped")

    def stop(self) -> None:
        """Stops the replica."""
        self._exit.set()
        self._logger.info(f"{self._name}: Stop signal received")

    def get_id(self) -> str:
        """Returns the id of the replica."""
        return self._initial_request._id

    # === MAIN AUCTION LOOP ===

    def _main_auction_loop(self):
        """Handles the main auction tasks of the replica."""
        assert self.auction is not None

        while not self._exit.is_set():
            # Start Leader tasks
            if self._is_leader:
                self._logger.info(f"{self._name}: LEADER: Starting auction manager")
                self._auction_manager = AuctionManager(self.auction)
                self._auction_manager.start()

            # Start Heartbeat
            self._heartbeat()

            # TODO: Implement actual election
            if self.reelection.is_set():
                self._logger.info(f"{self._name}: REELECTION: Started")
                self._election()
                self.reelection.clear()
                self._logger.info(f"{self._name}: REELECTION: Stopped")

        # Stop Leader tasks
        if self._is_leader and self._auction_manager is not None:
            self._logger.info(f"{self._name}: LEADER: Stopping auction manager")
            self._auction_manager.stop()
            self._auction_manager.join()

    # === PRELUDE ===

    def _prelude(self) -> None:
        """Handles the prelude of the replica.

        This initializes the replica to be ready to handle the auction either as a leader or follower.

        This is done through the following steps:
            - Responding to the replica-searcher replica request to indicate that the replica is available.
            - Waiting for the replica-searcher to acknowledge the response.
            - Waiting for the auctioneer to send the state of the auction.
            - Starting the listeners and sending an acknowledgement to the replica-searcher to indicate that the replica is ready to handle the auction.

        If the replica does not receive confirmation from the replica-searcher or the auction in time, the replica will set the stop signal.
        """
        self._logger.info(f"{self._name}: PRELUDE: Started")

        # Send response to auctioneer
        self._unicast.send(
            MessageFindReplicaResponse(_id=self._initial_request._id).encode(),
            self._initial_sender,
        )
        self._logger.info(
            f"{self._name}: PRELUDE: Replica response sent to {self._initial_sender}"
        )

        # Wait for auctioneer to acknowledge, or timeout
        self._logger.info(f"{self._name}: PRELUDE: Waiting for acknowledgement")
        try:
            self._wait_acknowledge()
        except TimeoutError:
            self._logger.info(
                f"{self._name}: PRELUDE: Acknowledgement not received; Exiting"
            )
            self.stop()
            return
        self._logger.info(f"{self._name}: PRELUDE: Acknowledgement received")

        # Wait for auctioneer to send auction information, or timeout
        self._logger.info(f"{self._name}: PRELUDE: Waiting for auction information")
        try:
            self._wait_information()
        except TimeoutError:
            self._logger.info(
                f"{self._name}: PRELUDE: Auction information not received; Exiting"
            )
            self.stop()
            return

        # Finalize prelude
        self._finalize_prelude()

        self._logger.info(f"{self._name}: PRELUDE: Prelude concluded")

    def _wait_acknowledge(self) -> None:
        """Waits for the auctioneer to acknowledge the response message.

        Raises:
            TimeoutError: If the auctioneer did not acknowledge the response message in time.
        """
        with Timeout(TIMEOUT_REPLICATION, throw_exception=True):
            while not self._exit.is_set():
                try:
                    message, address = self._unicast.receive(BUFFER_SIZE)
                except TimeoutError:
                    continue

                # Check if message is an acknowledgement from the replica searcher
                if (
                    not MessageSchema.of(com.HEADER_FIND_REPLICA_ACK, message)
                    or MessageSchema.get_id(message) != self._initial_request._id
                    or address != self._initial_sender
                ):
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
                    message, address = self._unicast.receive(BUFFER_SIZE)
                except TimeoutError:
                    continue

                if (
                    not MessageSchema.of(com.HEADER_AUCTION_INFORMATION_RES, message)
                    or MessageSchema.get_id(message) != self._initial_request._id
                    or address != self._initial_sender
                ):
                    continue

                response: MessageAuctionInformationResponse = (
                    MessageAuctionInformationResponse.decode(message)
                )

                self._handle_auction_information_message(response)

                break

            self._logger.info(
                f"{self._name}: PRELUDE: Auction information received: {self.auction}"
            )

    def _finalize_prelude(self) -> None:
        """Finalizes the prelude by starting the listeners and
        sending an acknowledgement to the replica searcher
        to indicate that the replica is ready to handle the auction.
        """
        self._logger.info(f"{self._name}: PRELUDE: Finalizing prelude")

        self._start_listeners()

        self._unicast.send(
            MessageAuctionInformationAcknowledgement(
                _id=self._initial_request._id
            ).encode(),
            self._initial_sender,
        )
        self._logger.info(
            f"{self._name}: PRELUDE: Auction information acknowledgement sent to {self._initial_sender}"
        )

        self._logger.info(f"{self._name}: PRELUDE: Prelude finalized")

    # === ELECTION ===

    def _election(self) -> None:
        """Handles the election of the replica.

        # TODO: Implement actual election, this is just a placeholder
        """
        self._logger.info(f"{self._name}: ELECTION: Started")
        self._is_leader = True
        self._leader = self._unicast.get_address()
        self._logger.info(f"{self._name}: ELECTION: Stopped")

    # === HEARTBEAT ===

    def _heartbeat(self) -> None:
        """Handles the heartbeat of the replica."""
        if self._is_leader:
            self._heartbeat_sender()
        else:
            self._heartbeat_listener()

    def _heartbeat_sender(self) -> None:
        """Handles the heartbeat emission of heartbeats and removal of unresponsive replicas."""
        assert self.auction is not None
        assert self.peers is not None

        self._logger.info(f"{self._name}: HEARTBEAT SENDER: Started")

        while not self.reelection.is_set() and not self._exit.is_set():
            # Create peers dict for keeping track of unresponsive peers
            responses: dict[tuple[IPv4Address, int], bool] = {
                replica: False
                for replica in self.peers.iter()
                if replica != self._unicast.get_host()
            }

            # Emit heartbeat and listen for responses
            heartbeat_id: str = self._heartbeat_emit(responses)
            try:
                self._heartbeat_response_listener(heartbeat_id, responses)
            except TimeoutError:
                self._logger.info(
                    f"{self._name}: HEARTBEAT SENDER: Timeout; Certain peers are unresponsive"
                )

            # Check if peer change or exit signal was set during heartbeat
            if self.reelection.is_set() or self._exit.is_set():
                break

            # Handle unresponsive peers
            unresponsive_peers: list[tuple[IPv4Address, int]] = [
                replica for replica, responded in responses.items() if not responded
            ]
            if len(unresponsive_peers) > 0:
                self._logger.info(
                    f"{self._name}: HEARTBEAT SENDER: Unresponsive peers: {unresponsive_peers}"
                )
                self._handle_unresponsive_replicas(unresponsive_peers)

        self._logger.info(f"{self._name}: HEARTBEAT SENDER: Stopped")

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
            f"{self._name}: HEARTBEAT SENDER: Emitting heartbeats with id {heartbeat_id}"
        )
        for replica in replicas.keys():
            self._unicast.send(heartbeat, replica)

        self._logger.info(f"{self._name}: HEARTBEAT SENDER: Heartbeats emitted")

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
            f"{self._name}: HEARTBEAT SENDER: Listening for heartbeat responses from {replicas.keys()}"
        )
        with Timeout(TIMEOUT_HEARTBEAT, throw_exception=True):
            while (
                not self.reelection.is_set()
                and not self._exit.is_set()
                and not all(replicas.values())
            ):
                try:
                    response, address = self._unicast.receive(BUFFER_SIZE)
                except TimeoutError:
                    continue

                if not MessageSchema.of(com.HEADER_HEARTBEAT_RES, response):
                    continue

                heartbeat_response: MessageHeartbeatResponse = (
                    MessageHeartbeatResponse.decode(response)
                )

                if heartbeat_response._id != heartbeat_id:
                    self._logger.info(
                        f"{self._name}: HEARTBEAT SENDER: Received heartbeat {heartbeat_response._id} for another heartbeat {heartbeat_id}"
                    )
                    continue

                if address not in replicas.keys():
                    self._logger.error(
                        f"{self._name}: HEARTBEAT SENDER: Received heartbeat from unknown replica {address}"
                    )
                    continue

                self._logger.info(
                    f"{self._name}: HEARTBEAT SENDER: Received heartbeat {heartbeat_response._id} from {address}"
                )
                replicas[address] = True

    def _heartbeat_listener(self) -> None:
        """Handles the heartbeat listener of the replica.

        If the replica does not receive a heartbeat from the leader in time, the replica will set the reelection signal.
        """
        self._logger.info(f"{self._name}: HEARTBEAT LISTENER: Started")
        while not self.reelection.is_set() and not self._exit.is_set():
            try:
                with Timeout(TIMEOUT_HEARTBEAT, throw_exception=True):
                    while not self.reelection.is_set() and not self._exit.is_set():
                        try:
                            response, address = self._unicast.receive(BUFFER_SIZE)
                        except TimeoutError:
                            continue

                        if (
                            not MessageSchema.of(com.HEADER_HEARTBEAT_REQ, response)
                            or address != self._leader
                        ):
                            continue

                        heartbeat: MessageHeartbeatRequest = (
                            MessageHeartbeatRequest.decode(response)
                        )
                        self._unicast.send(
                            MessageHeartbeatResponse(_id=heartbeat._id).encode(),
                            self._leader,
                        )

                        self._logger.info(
                            f"{self._name}: HEARTBEAT LISTENER: Received heartbeat {heartbeat._id} from {address}; Responded"
                        )

                        break
            except TimeoutError:
                self._logger.info(
                    f"{self._name}: HEARTBEAT LISTENER: Timeout; Starting election"
                )
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
            f"{self._name}: HEARTBEAT SENDER: Handling unresponsive peers"
        )

        for replica in unresponsive_peers:
            self.peers.remove(*replica)

        # Start replica finder in background if there are not enough replicas
        if self.peers.len() <= REPLICA_AUCTION_POOL_SIZE:
            if self._replica_finder is None or not self._replica_finder.is_alive():
                self._logger.info(
                    f"{self._name}: HEARTBEAT SENDER: Starting replica finder"
                )
                self._replica_finder = ReplicaFinder(
                    self.auction, self.peers, REPLICA_EMITTER_PERIOD
                )
            else:
                self._logger.info(
                    f"{self._name}: HEARTBEAT SENDER: Replica finder already running"
                )

        self._logger.info(f"{self._name}: HEARTBEAT SENDER: Unresponsive peers handled")

    def _handle_auction_information_message(
        self,
        message: MessageAuctionInformationResponse,
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
            rcv_auction.get_time(),
            rcv_auction.get_group(),
        )

        assert self.auction is not None
        self.auction.from_other(rcv_auction)

    def _handle_stop(self) -> None:
        """Handles the stopping of the replica."""
        self._logger.info(f"{self._name}: Stopping replica")

        self._unicast.close()
        self._stop_listeners()

        self.manager_running.clear()
        self.manager.shutdown()

    # === HELPERS ===

    def _init_shared_memory(self):
        """Initializes the shared memory."""
        self.manager.start()
        self.manager_running.set()
        self._logger.info(f"{self._name}: Started manager")

        self.peers: Optional[AuctionPeersStore] = self.manager.AuctionPeersStore()  # type: ignore

    def _start_listeners(self) -> None:
        """Starts the listeners after the auction information is received."""
        # Asserts
        assert self.auction is not None
        assert self.peers is not None

        # Start listeners
        self._logger.info(f"{self._name}: PRELUDE: Starting listeners")

        self._auction_peers_listener: Optional[
            AuctionPeersAnnouncementListener
        ] = AuctionPeersAnnouncementListener(self.auction, self.peers, self.peer_change)
        self._auction_bid_listener: Optional[AuctionBidListener] = AuctionBidListener(
            self.auction
        )

        self._auction_peers_listener.start()
        self._auction_bid_listener.start()

        self._logger.info(f"{self._name}: PRELUDE: Listeners started")

    def _stop_listeners(self):
        """Stops the listeners."""

        self._logger.info(f"{self._name}: Stopping listeners")

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

        self._logger.info(f"{self._name}: Listeners stopped")
