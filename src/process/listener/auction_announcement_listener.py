from typing import Optional

from ipaddress import IPv4Address

from multiprocessing import Process, Event as ProcessEvent
from multiprocessing.synchronize import Event

from logging import Logger

# === Custom Modules ===

from communication import Multicast, MessageSchema, MessageAuctionAnnouncement
from constant.state.auction import AUCTION_CANCELLED, AUCTION_ENDED
from model import Auction, AuctionAnnouncementStore
from util import create_logger

from constant import (
    communication as com,
    stateid2stateobj,
    USERNAME,
    COMMUNICATION_BUFFER_SIZE,
    COMMUNICATION_TIMEOUT,
    MULTICAST_DISCOVERY_GROUP,
    MULTICAST_DISCOVERY_PORT,
    MULTICAST_AUCTION_ANNOUNCEMENT_PORT,
    AUCTION_CANCELLED,
    AUCTION_ENDED,
)


class AuctionAnnouncementListener(Process):
    """Auction announcement listener process.

    This process listens to auction announcements on the multicast discovery channel.
    """

    def __init__(
        self,
        auction_announcement_store: AuctionAnnouncementStore,
        auction_id: Optional[str] = None,
        auction_group: Optional[IPv4Address] = None,
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

        self._auction_id: str = auction_id if auction_id else ""
        self._high_frequency: bool = bool(self._auction_id and auction_group)
        self._auction_group: IPv4Address = (
            auction_group if auction_group else MULTICAST_DISCOVERY_GROUP
        )
        self._auction_port: int = (
            MULTICAST_AUCTION_ANNOUNCEMENT_PORT
            if self._high_frequency
            else MULTICAST_DISCOVERY_PORT
        )

    def run(self) -> None:
        """Runs the auction listener process."""
        self._logger.info(
            f"{self._prefix}: Initialized for {(self._auction_group, self._auction_port)} with {self._auction_id if self._auction_id else 'all auctions'}"
        )

        self._logger.info(f"{self._prefix}: Started")
        mc: Multicast = Multicast(
            group=self._auction_group,
            port=self._auction_port,
            timeout=COMMUNICATION_TIMEOUT,
        )

        self._logger.info(f"{self._prefix}: Listening for auction announcements")
        while not self._exit.is_set():
            # Receive announcement
            try:
                message, _ = mc.receive(COMMUNICATION_BUFFER_SIZE)
            except TimeoutError:
                continue

            if (
                not MessageSchema.of(com.HEADER_AUCTION_ANNOUNCEMENT, message)
                or message in self._seen_message_ids
            ):
                continue

            try:
                if (
                    self._high_frequency
                    and Auction.parse_id(MessageSchema.get_id(message))
                    != self._auction_id
                ):
                    self._logger.info(
                        f"{self._prefix}: Received announcement for different auction on same multicast: {message}"
                    )
                    continue
            except ValueError:
                self._logger.error(
                    f"{self._prefix}: Invalid message ID for message {message}"
                )
                continue

            announcement: MessageAuctionAnnouncement = (
                MessageAuctionAnnouncement.decode(message)
            )
            self._logger.info(
                f"{self._prefix}: Received announcement for auction: {announcement}"
            )

            self._seen_message_ids.append(announcement._id)
            self._store.update(announcement)

            if self._high_frequency and stateid2stateobj[
                announcement.auction.state
            ] in [AUCTION_CANCELLED, AUCTION_ENDED]:
                self._logger.info(
                    f"{self._prefix}: Auction {announcement.auction._id} has ended or been cancelled, stopping listener"
                )
                break

        self._logger.info(f"{self._prefix}: Releasing resources")

        mc.close()

        self._logger.info(f"{self._prefix}: Stopped")

    def stop(self) -> None:
        """Stops the auction listener process."""
        self._exit.set()
        self._logger.info(f"{self._prefix}: Stop signal received")
