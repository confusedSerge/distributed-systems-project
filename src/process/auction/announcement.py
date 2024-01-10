from multiprocessing import Process, Event

from communication import Multicast, MessageSchema, MessageAuctionAnnouncement

from model.auction_announcement_store import AuctionAnnouncementStore
from constant import (
    header as hdr,
    TIMEOUT_RECEIVE,
    MULTICAST_DISCOVERY_GROUP,
    MULTICAST_DISCOVERY_PORT,
)

from util import create_logger


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
        self._exit = Event()

        self._store: AuctionAnnouncementStore = auction_announcement_store

        self.name = "AuctionAnnouncementListener"
        self.logger = create_logger(self.name.lower())

    def run(self) -> None:
        """Runs the auction listener process."""
        self.logger.info(f"{self.name} is starting background tasks")
        mc = Multicast(
            MULTICAST_DISCOVERY_GROUP, MULTICAST_DISCOVERY_PORT, timeout=TIMEOUT_RECEIVE
        )

        while not self._exit.is_set():
            # Receive announcement
            try:
                announcement, address = mc.receive()
            except TimeoutError:
                continue

            if not MessageSchema.of(hdr.AUCTION_ANNOUNCEMENT, announcement):
                continue

            announcement: MessageAuctionAnnouncement = (
                MessageAuctionAnnouncement.decode(announcement)
            )
            if not self._store.exists(announcement.auction_id):
                self.logger.info(
                    f"{self.name} received new announcement {announcement} from {address}"
                )
                self._store.add(announcement)

        self.logger.info(f"{self.name} received stop signal; releasing resources")
        mc.close()

        self.logger.info(f"{self.name} stopped listening to auction announcements")

    def stop(self) -> None:
        """Stops the auction listener process."""
        self.logger.info(f"{self.name} received stop signal")
        self._exit.set()
