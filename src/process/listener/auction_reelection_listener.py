import os

from ipaddress import IPv4Address

from multiprocessing import Process, Event as ProcessEvent
from multiprocessing.synchronize import Event

from logging import Logger

# === Custom Modules ===

from communication import (
    Unicast,
    MessageSchema,
    MessageElectionRequest,
    MessageElectionAnswer,
    MessageElectionCoordinator,
)
from model import Leader
from util import create_logger

from constant import (
    communication as com,
    TIMEOUT_RECEIVE,
    ELECTION_PORT,
    HEADER_ELECTION_REQ,
    HEADER_ELECTION_COORDINATOR,
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

        self._name: str = f"AuctionReelectionListener::{os.getpid()}"
        self._logger: Logger = create_logger(self._name.lower())

        self._own_id: tuple[str, int] = own_id
        self._leader: Leader = leader
        self._reelect: Event = reelect
        self._coordinator: Event = coordinator

        self._logger.info(f"{self._name}: Initialized")

    def run(self) -> None:
        """Runs the auction reelection listener process."""
        self._logger.info(f"{self._name}: Started")
        uc: Unicast = Unicast(
            TIMEOUT_RECEIVE,
            port=ELECTION_PORT,
        )

        self._logger.info(f"{self._name}: Listening for reelection messages")
        while not self._exit.is_set():
            # Receive message
            try:
                message, address = uc.receive()
            except TimeoutError:
                continue

            if not MessageSchema.of(
                HEADER_ELECTION_REQ, message
            ) and not MessageSchema.of(HEADER_ELECTION_COORDINATOR, message):
                continue

            if MessageSchema.of(HEADER_ELECTION_REQ, message):
                election: MessageElectionRequest = MessageElectionRequest.decode(
                    message
                )
                self._handle_election(election, address)

            if MessageSchema.of(HEADER_ELECTION_COORDINATOR, message):
                coordinator: MessageElectionCoordinator = (
                    MessageElectionCoordinator.decode(message)
                )
                self._handle_coordinator(coordinator, address)

            assert False, "Unreachable code"

        self._logger.info(f"{self._name}: Stopped")

    def stop(self) -> None:
        """Stops the auction reelection listener process."""
        self._logger.info(f"{self._name}: Stopping")
        self._exit.set()
        self._logger.info(f"{self._name}: Stopped")

    def _handle_election(
        self, message: MessageElectionRequest, address: tuple[IPv4Address, int]
    ) -> None:
        """Handle an election request message.

        Args:
            message (MessageElectionRequest): The election request message.
            address (tuple[IPv4Address, int]): The address of the sender.
        """
        if self._own_id < message.req_id:
            self._logger.info(
                f"{self._name}: Received election request from {message._id} with higher id."
            )
            return

        self._logger.info(
            f"{self._name}: Received election request from {message._id} with lower id. Sending election answer and starting election process"
        )
        answer: MessageElectionAnswer = MessageElectionAnswer(
            _id=message._id,
            req_id=self._own_id,
        )
        Unicast.qsend(
            message=answer.encode(),
            host=address[0],
            port=address[1],
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
                f"{self._name}: Received coordinator message from {message._id} with higher id. Found new coordinator. Setting coordinator flag and updating leader"
            )
            self._leader.set(*address)
            self._coordinator.set()
            return

        self._logger.info(
            f"{self._name}: Received coordinator message from {message._id} with lower id. Setting reelect flag"
        )
        self._reelect.set()
