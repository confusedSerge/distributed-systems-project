from typing import Optional

from ipaddress import IPv4Address

from multiprocessing import Process, Event as ProcessEvent
from multiprocessing.synchronize import Event

from logging import Logger

# === Custom Modules ===

from communication import Multicast, MessageSchema, MessageAuctionAnnouncement
from model import AuctionAnnouncementStore
from util import create_logger

from constant import (
    communication as com,
    USERNAME,
    TIMEOUT_RECEIVE,
    BUFFER_SIZE,
    MULTICAST_DISCOVERY_GROUP,
    MULTICAST_DISCOVERY_PORT,
    MULTICAST_AUCTION_PORT,
)


class AuctionAnnouncementListener(Process):
    """Auction announcement listener process.

    This process listens to auction announcements on the multicast discovery channel.
    """

    def __init__(
        self,
        auction_announcement_store: AuctionAnnouncementStore,
        auction_id: str = "",
    ):
        """Initializes the auction listener process.

        Args:
            auction_announcement_store (AuctionAnnouncementStore): The auction announcement store to listen to. Should be a shared memory object.
        """
        super(AuctionAnnouncementListener, self).__init__()
        self._exit: Event = ProcessEvent()

        self._name: str = self.__class__.__name__.lower()
        self._prefix: str = f"{self._name}::{USERNAME}"
        self._logger: Logger = create_logger(self._name, with_pid=True)

        self._seen_message_ids: list[str] = []
        self._store: AuctionAnnouncementStore = auction_announcement_store

        self._auction_id: str = auction_id
        self._high_frequency: bool = self._auction_id is not None
        self._address: tuple[IPv4Address, int] = (
            (MULTICAST_DISCOVERY_GROUP, MULTICAST_DISCOVERY_PORT)
            if self._high_frequency
            else (
                IPv4Address(self._store.get(self._auction_id).auction.group),
                MULTICAST_AUCTION_PORT,
            )
        )

        self._logger.info(f"{self._name}: Initialized")

    def run(self) -> None:
        """Runs the auction listener process."""

        self._logger.info(f"{self._name}: Started")
        mc: Multicast = Multicast(
            group=self._address[0],
            port=self._address[1],
            timeout=TIMEOUT_RECEIVE,
        )

        self._logger.info(f"{self._name}: Listening for auction announcements")
        while not self._exit.is_set():
            # Receive announcement
            try:
                message, _ = mc.receive(BUFFER_SIZE)
            except TimeoutError:
                continue

            if (
                not MessageSchema.of(com.HEADER_AUCTION_ANNOUNCEMENT, message)
                or message in self._seen_message_ids
                or (
                    self._high_frequency
                    and MessageAuctionAnnouncement.decode(message)._id
                    != self._auction_id
                )
            ):
                continue

            announcement: MessageAuctionAnnouncement = (
                MessageAuctionAnnouncement.decode(message)
            )
            self._logger.info(
                f"{self._name}: Received announcement for auction {announcement._id}: {announcement}"
            )

            self._seen_message_ids.append(announcement._id)
            self._store.update(announcement)

        self._logger.info(f"{self._name}: Releasing resources")

        mc.close()

        self._logger.info(f"{self._name}: Stopped")

    def stop(self) -> None:
        """Stops the auction listener process."""
        self._exit.set()
        self._logger.info(f"{self._name}: Stop signal received")
