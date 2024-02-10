import os

from ipaddress import IPv4Address

from multiprocessing import Process, Event as ProcessEvent
from multiprocessing.synchronize import Event

from logging import Logger

# === Custom Modules ===

from communication import (
    ReliableUnicast,
    MessageSchema,
    MessageElectionRequest,
    MessageElectionAnswer,
    MessageElectionCoordinator,
)
from model import Leader, Auction
from util import create_logger

from constant import (
    HEADER_ELECTION_REQ,
    HEADER_ELECTION_COORDINATOR,
    COMMUNICATION_RELIABLE_RETRIES,
    COMMUNICATION_RELIABLE_TIMEOUT,
    REPLICA_ELECTION_PORT,
)


class AuctionReelectionListener(Process):
    """Auction reelection listener process.

    This process listens to two types of messages:
    - Election messages
    - Coordinator messages

    If an election message is received, the process will respond with an election answer message
        and will start an election process if it is not already running (done by setting a flag).

    If a coordinator message is received and compare against own replica id,
        - lower: start an election process by setting a flag
        - higher: note the coordinator and set coordinator flag

    Both messages are received on a unicast message with corresponding port.
    """

    def __init__(
        self,
        own_id: tuple[str, int],
        leader: Leader,
        reelect: Event,
        coordinator: Event,
        auction_id: str,
    ):
        """Initializes the auction reelection listener process.

        Args:
            own_id (tuple[str, int]): Own replica id.
            leader (Leader): The leader object to update.
            reelect (Event): The event to set when an election process should start.
            coordinator (Event): The event to set when a coordinator is elected.
        """

        super(AuctionReelectionListener, self).__init__()
        self._exit: Event = ProcessEvent()

        self._name: str = self.__class__.__name__.lower()
        self._prefix: str = f"{self._name}::{auction_id}"
        self._logger: Logger = create_logger(self._name, with_pid=True)

        self._auction_id: str = auction_id
        self._own_id: tuple[str, int] = own_id
        self._leader: Leader = leader
        self._reelect: Event = reelect
        self._coordinator: Event = coordinator

        self._seen_message_ids: list[str] = []

    def run(self) -> None:
        """Runs the auction reelection listener process."""
        self._logger.info(f"{self._prefix}: Initialized for {self._auction_id}")

        self._logger.info(f"{self._prefix}: Started")
        uc: ReliableUnicast = ReliableUnicast(
            timeout=COMMUNICATION_RELIABLE_TIMEOUT,
            retry=COMMUNICATION_RELIABLE_RETRIES,
            port=REPLICA_ELECTION_PORT,
        )

        self._logger.info(f"{self._prefix}: Listening for reelection messages")
        while not self._exit.is_set():
            # Receive message
            try:
                message, address = uc.receive()
            except TimeoutError:
                continue

            if (
                not MessageSchema.of(HEADER_ELECTION_REQ, message)
                and not MessageSchema.of(HEADER_ELECTION_COORDINATOR, message)
                or MessageSchema.get_id(message) in self._seen_message_ids
            ):
                continue

            try:
                parsed_id = Auction.parse_id(MessageSchema.get_id(message))
            except ValueError:
                self._logger.info(
                    f"{self._prefix}: Received message with invalid auction id: {message}"
                )
                continue

            if parsed_id != self._auction_id:
                self._logger.info(
                    f"{self._prefix}: Ignoring received message from {address} for different auction {parsed_id} (expected {self._auction_id}): {message}"
                )
                continue

            if MessageSchema.of(HEADER_ELECTION_REQ, message):
                election: MessageElectionRequest = MessageElectionRequest.decode(
                    message
                )
                self._handle_election(election, uc, address)
                self._seen_message_ids.append(election._id)
                continue

            if MessageSchema.of(HEADER_ELECTION_COORDINATOR, message):
                coordinator: MessageElectionCoordinator = (
                    MessageElectionCoordinator.decode(message)
                )
                self._handle_coordinator(coordinator, address)
                self._seen_message_ids.append(coordinator._id)
                continue

            self._logger.error(
                f"{self._prefix}: Unreachable code with message {message}"
            )
            assert False, "Unreachable code"

        self._logger.info(f"{self._prefix}: Stopped")

    def stop(self) -> None:
        """Stops the auction reelection listener process."""
        self._logger.info(f"{self._prefix}: Received stop signal")
        self._exit.set()

    def _handle_election(
        self,
        message: MessageElectionRequest,
        uc: ReliableUnicast,
        address: tuple[IPv4Address, int],
    ) -> None:
        """Handle an election request message.

        Args:
            message (MessageElectionRequest): The election request message.
            uc (ReliableUnicast): The unicast communication object.
            address (tuple[IPv4Address, int]): The address of the sender.
        """
        if self._own_id < message.req_id:
            self._logger.info(
                f"{self._prefix}: Received election request with higher id ({self._own_id}, (Ignored)): {message}"
            )
            return

        self._logger.info(
            f"{self._prefix}: Received election request with lower id ({self._own_id}, (Answered)): {message}"
        )
        answer: MessageElectionAnswer = MessageElectionAnswer(
            _id=message._id,
            req_id=self._own_id,
        )
        uc.send(
            message=answer.encode(),
            address=address,
        )

        self._reelect.set()

    def _handle_coordinator(
        self, message: MessageElectionCoordinator, address: tuple[IPv4Address, int]
    ) -> None:
        """Handle a coordinator message.

        Args:
            message (MessageElectionCoordinator): The coordinator message.
            address (tuple[IPv4Address, int]): The address of the sender.
        """
        if self._own_id < message.req_id:
            self._logger.info(
                f"{self._prefix}: Received coordinator message with higher id ({self._own_id}, (New Leader)): {message}"
            )
            self._leader.set(*address)
            self._coordinator.set()
            return

        self._logger.info(
            f"{self._prefix}: Received coordinator message with lower id ({self._own_id}, (Reelection)): {message}"
        )
        self._reelect.set()
