from multiprocessing import Process, Event

from communication import Multicast, MessageSchema, MessageAuctionAnnouncement

from model.auction_announcement_store import AuctionAnnouncementStore
from constant import (
    header as hdr,
    MULTICAST_DISCOVERY_GROUP,
    MULTICAST_DISCOVERY_PORT,
)

from util import create_logger


class AuctionAnnouncementListener(Process):
    """Auction announcement listener process.

    This process listens to auction announcements on the multicast discovery channel.
    """

    def __init__(self, auction: AuctionAnnouncementStore):
        """Initializes the auction listener process.

        Args:
            auction (AuctionAnnouncementStore): The auction announcement store to listen to. Should be a shared memory object.
        """
        super().__init__()
        self._exit = Event()

        self._store: AuctionAnnouncementStore = auction

        self.name = f"AuctionAnnouncementListener-{auction.get_id()}"
        self.logger = create_logger(self.name.lower())

    def run(self) -> None:
        """Runs the auction listener process."""
        self.logger.info(f"{self.name} is starting background tasks")
        mc = Multicast(MULTICAST_DISCOVERY_GROUP, MULTICAST_DISCOVERY_PORT)

        while not self._exit.is_set():
            # Receive announcement
            announcement, address = mc.receive()

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

    def stop(self) -> None:
        """Stops the auction listener process."""
        self.logger.info(f"{self.name} received stop signal")
        self._exit.set()
