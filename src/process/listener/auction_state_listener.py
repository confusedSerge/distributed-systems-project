import os

from multiprocessing import Process, Event as ProcessEvent
from multiprocessing.synchronize import Event

from logging import Logger

# === Custom Modules ===

from model import Auction
from communication import (
    AdjustedIsisRMulticast,
    MessageSchema,
    MessageAuctionStateAnnouncement,
)
from util import create_logger

from constant import (
    communication as com,
    COMMUNICATION_BUFFER_SIZE,
    COMMUNICATION_TIMEOUT,
    MULTICAST_AUCTION_STATE_ANNOUNCEMENT_PORT,
)


class AuctionStateAnnouncementListener(Process):
    """Auction state announcement listener process.

    This process listens to auction state announcements on the multicast auction channel and updates the auction of the replica accordingly.
    """

    def __init__(self, auction: Auction):
        """Initializes the auction state announcement listener process.

        Args:
            auction (Auction): The auction to update. Should be a shared memory object.
        """
        super(AuctionStateAnnouncementListener, self).__init__()
        self._exit: Event = ProcessEvent()

        self._name: str = self.__class__.__name__.lower()
        self._prefix: str = f"{self._name}::{auction.get_id()}"
        self._logger: Logger = create_logger(self._name, with_pid=True)

        self._auction: Auction = auction
        self._seen_message_id: list[str] = []

    def run(self) -> None:
        """Runs the auction listener process."""
        self._logger.info(f"{self._prefix}: Initialized for {self._auction.get_id()}")

        self._logger.info(f"{self._prefix}: Started")
        mc: AdjustedIsisRMulticast = AdjustedIsisRMulticast(
            group=self._auction.get_group(),
            port=MULTICAST_AUCTION_STATE_ANNOUNCEMENT_PORT,
            timeout=COMMUNICATION_TIMEOUT,
        )

        self._logger.info(
            f"{self._prefix}: Listening for state announcements on auction"
        )
        while not self._exit.is_set():
            # Receive state announcement
            try:
                message, address = mc.deliver()
            except TimeoutError:
                continue

            # Decode message
            if (
                not MessageSchema.of(com.HEADER_AUCTION_STATE_ANNOUNCEMENT, message)
                or MessageSchema.get_id(message) in self._seen_message_id
            ):
                continue

            state_announcement: MessageAuctionStateAnnouncement = (
                MessageAuctionStateAnnouncement.decode(message)
            )

            try:
                parsed_id = Auction.parse_id(state_announcement._id)
            except ValueError:
                self._logger.info(
                    f"{self._prefix}: Received auction state announcement with invalid auction id: {state_announcement}"
                )
                continue

            if parsed_id != self._auction.get_id():
                self._logger.info(
                    f"{self._prefix}: Ignoring received auction state announcement from {address} for different auction {parsed_id} (expected {self._auction.get_id()}): {state_announcement}"
                )
                continue

            self._seen_message_id.append(state_announcement._id)

            # Update auction state
            self._auction.set_state(state_announcement.state)
            self._logger.info(
                f"{self._prefix}: Updated auction state to {self._auction.get_state()}"
            )

        self._logger.info(f"{self._prefix}: Stop signal received")

        mc.close()

        self._logger.info(f"{self._prefix}: Stopped")

    def stop(self) -> None:
        """Stops the auction listener process."""
        self._exit.set()
        self._logger.info(f"{self._prefix}: Stop signal received")
