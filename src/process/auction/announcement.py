import os

from multiprocessing import Process, Event

from communication import Multicast, MessageSchema, MessageAuctionAnnouncement

from model import AuctionAnnouncementStore
from constant import (
    communication as com,
    USERNAME,
    TIMEOUT_RECEIVE,
    BUFFER_SIZE,
    MULTICAST_DISCOVERY_GROUP,
    MULTICAST_DISCOVERY_PORT,
)

from util import create_logger, logger


class AuctionAnnouncementListener(Process):
    """Auction announcement listener process.

    This process listens to auction announcements on the multicast discovery channel.
    """

    def __init__(self, auction_announcement_store: AuctionAnnouncementStore):
        """Initializes the auction listener process.

        Args:
            auction_announcement_store (AuctionAnnouncementStore): The auction announcement store to listen to. Should be a shared memory object.
        """
        super(AuctionAnnouncementListener, self).__init__()
        self._exit: Event = Event()

        self._name: str = f"AuctionAnnouncementListener::{USERNAME}::{os.getpid()}"
        self._logger: logger = create_logger(self._name.lower())

        self._store: AuctionAnnouncementStore = auction_announcement_store

        self._logger.info(f"{self._name}: Initialized")

    def run(self) -> None:
        """Runs the auction listener process."""
        self._logger.info(f"{self._name}: Started")
        mc: Multicast = Multicast(
            group=MULTICAST_DISCOVERY_GROUP,
            port=MULTICAST_DISCOVERY_PORT,
            timeout=TIMEOUT_RECEIVE,
        )

        self._logger.info(f"{self._name}: Listening for auction announcements")
        while not self._exit.is_set():
            # Receive announcement
            try:
                announcement, _ = mc.receive(BUFFER_SIZE)
            except TimeoutError:
                continue

            if not MessageSchema.of(com.HEADER_AUCTION_ANNOUNCEMENT, announcement):
                continue

            announcement: MessageAuctionAnnouncement = (
                MessageAuctionAnnouncement.decode(announcement)
            )
            if not self._store.exists(announcement._id):
                self._logger.info(
                    f"{self._name}: Received announcement for auction {announcement._id}"
                )
                self._store.update(announcement)

        self._logger.info(f"{self._name}: Releasing resources")

        mc.close()

        self._logger.info(f"{self._name}: Stopped")

    def stop(self) -> None:
        """Stops the auction listener process."""
        self._exit.set()
        self._logger.info(f"{self._name}: Stop signal received")
