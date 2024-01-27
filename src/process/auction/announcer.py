import os

from time import sleep
from multiprocessing import Process, Event

from communication import Multicast, MessageSchema, MessageAuctionAnnouncement

from model import Auction
from constant import (
    MULTICAST_DISCOVERY_GROUP,
    MULTICAST_DISCOVERY_PORT,
)

from util import create_logger, logger, generate_message_id


class AuctionAnnouncer(Process):
    """Auction announcer process, periodically announces its auction on the multicast discovery channel.

    This process is used by the leader of an auction to announce the auction (and possible changes) to the discovery multicast group.
    """

    def __init__(self, auction: Auction, period: int = 60):
        """Initializes the auction announcer process.

        Args:
            auction (Auction): The auction to announce. Should be a shared memory object.
            period (int, optional): The period of the announcer. Defaults to 60 seconds.
        """
        super(AuctionAnnouncer, self).__init__()
        self._exit: Event = Event()

        self._name: str = f"AuctionAnnouncer::{auction.get_id()}::{os.getpid()}"
        self._logger: logger = create_logger(self._name.lower())

        self._auction: Auction = auction
        self._period: int = period

        self._logger.info(f"{self._name}: Initialized")

    def run(self) -> None:
        """Runs the auction announcer process."""
        self._logger.info(f"{self._name}: Started")
        mc: Multicast = Multicast(
            group=MULTICAST_DISCOVERY_GROUP,
            port=MULTICAST_DISCOVERY_PORT,
        )

        self._logger.info(
            f"{self._name}: Emitting auction announcements every {self._period} seconds"
        )
        while not self._exit.is_set():
            announcement: MessageAuctionAnnouncement = MessageAuctionAnnouncement(
                _id=generate_message_id(),
                auction=self._auction,
            )
            mc.send(announcement.encode())

            sleep(self._period)

        self._logger.info(f"{self._name}: Releasing resources")

        mc.close()

        self._logger.info(f"{self._name}: Stopped")

    def stop(self) -> None:
        """Stops the auction announcer process."""
        self._exit.set()
        self._logger.info(f"{self._name}: Stop signal received")
