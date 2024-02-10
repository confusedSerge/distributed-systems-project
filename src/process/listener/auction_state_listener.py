import os

from multiprocessing import Process, Event as ProcessEvent
from multiprocessing.synchronize import Event

from logging import Logger

# === Custom Modules ===

from model import Auction
from communication import Multicast, MessageSchema, MessageAuctionStateAnnouncement
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

        self._logger.info(f"{self._name}: Initialized")

    def run(self) -> None:
        """Runs the auction listener process."""
        self._logger.info(f"{self._name}: Started")
        mc: Multicast = Multicast(
            group=self._auction.get_group(),
            port=MULTICAST_AUCTION_STATE_ANNOUNCEMENT_PORT,
            timeout=COMMUNICATION_TIMEOUT,
        )

        self._logger.info(f"{self._name}: Listening for state announcements on auction")
        while not self._exit.is_set():
            # Receive state announcement
            try:
                message, address = mc.receive(COMMUNICATION_BUFFER_SIZE)
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
                    f"{self._name}: Received auction state announcement {state_announcement} with invalid auction id {state_announcement._id}"
                )
                continue

            if parsed_id != self._auction.get_id():
                self._logger.info(
                    f"{self._name}: Ignoring received auction state announcement from {address} for different auction {parsed_id} (expected {self._auction.get_id()})"
                )
                continue

            self._seen_message_id.append(state_announcement._id)

            # Update auction state
            self._auction.set_state(state_announcement.state)
            self._logger.info(
                f"{self._name}: Updated auction state to {self._auction.get_state()}"
            )

        self._logger.info(f"{self._name}: Stop signal received")

        mc.close()

        self._logger.info(f"{self._name}: Stopped")

    def stop(self) -> None:
        """Stops the auction listener process."""
        self._exit.set()
        self._logger.info(f"{self._name}: Stop signal received")
