from ipaddress import IPv4Address

from multiprocessing import Process, Event as ProcessEvent
from multiprocessing.synchronize import Event

from logging import Logger

# === Custom Modules ===

from communication import (
    RMulticast as Multicast,
    MessageSchema,
    MessageAuctionPeersAnnouncement,
)
from model import Auction, AuctionPeersStore
from util import create_logger

from constant import (
    communication as com,
    COMMUNICATION_BUFFER_SIZE,
    COMMUNICATION_TIMEOUT,
    MULTICAST_AUCTION_PEERS_ANNOUNCEMENT_PORT,
)


class AuctionPeersAnnouncementListener(Process):
    """Auction replica peers listener process.

    This process listens the peers announcement on the auction multicast group.
    """

    def __init__(
        self, auction: Auction, auction_peers_store: AuctionPeersStore, change: Event
    ) -> None:
        """Initializes the auction listener process.

        Args:
            auction (Auction): The auction to listen to.
            auction_peers_store (AuctionPeersStore): The auction peers store, used to store the peers.
        """
        super(AuctionPeersAnnouncementListener, self).__init__()
        self._exit: Event = ProcessEvent()

        self._name: str = self.__class__.__name__.lower()
        self._prefix: str = f"{self._name}::{auction.get_id()}"
        self._logger: Logger = create_logger(self._name, with_pid=True)

        self._auction: Auction = auction
        self._store: AuctionPeersStore = auction_peers_store
        self._change: Event = change
        self._seen_message_ids: list[str] = []

    def run(self) -> None:
        """Runs the auction listener process

        Listens for peers announcements on the auction multicast group.
        The peers are stored in the auction peers store.

        """
        self._logger.info(f"{self._prefix}: Initialized for {self._auction.get_id()}")

        self._logger.info(f"{self._prefix}: Started")
        mc: Multicast = Multicast(
            group=self._auction.get_group(),
            port=MULTICAST_AUCTION_PEERS_ANNOUNCEMENT_PORT,
            timeout=COMMUNICATION_TIMEOUT,
        )

        self._logger.info(
            f"{self._prefix}: Listening for peers announcements on {(self._auction.get_group(), MULTICAST_AUCTION_PEERS_ANNOUNCEMENT_PORT)} for auction {self._auction.get_id()} "
        )
        while not self._exit.is_set():
            # Receive announcement or timeout to check exit condition
            try:
                message, address = mc.deliver()
            except TimeoutError:
                continue

            # Ignore if message is not a peers announcement or if the message has already been seen
            if (
                not MessageSchema.of(com.HEADER_AUCTION_PEERS_ANNOUNCEMENT, message)
                or MessageSchema.get_id(message) in self._seen_message_ids
            ):
                continue

            # Decode message and store peers
            peers_announcement: MessageAuctionPeersAnnouncement = (
                MessageAuctionPeersAnnouncement.decode(message)
            )

            try:
                parsed_id = Auction.parse_id(peers_announcement._id)
            except ValueError:
                self._logger.info(
                    f"{self._prefix}: Received peers announcement with invalid auction id: {peers_announcement}"
                )
                continue

            if parsed_id != self._auction.get_id():
                self._logger.info(
                    f"{self._prefix}: Ignoring received peer list from {address} for different auction {parsed_id} (expected {self._auction.get_id()}): {peers_announcement}"
                )
                continue

            peers: list[tuple[IPv4Address, int]] = [
                (IPv4Address(peer[0]), peer[1]) for peer in peers_announcement.peers
            ]

            self._logger.info(f"{self._prefix}: Received peers announcement: {peers}")

            self._seen_message_ids.append(peers_announcement._id)
            changes: bool = self._store.replace(peers)

            # Set change event if changes were made
            if not changes:
                continue

            self._logger.info(
                f"{self._prefix}: Peers announcement caused changes in the store"
            )
            self._change.set()

        self._logger.info(f"{self._prefix}: Releasing resources")
        mc.close()

        self._logger.info(f"{self._prefix}: Stopped")

    def stop(self) -> None:
        """Stops the auction listener process."""
        self._exit.set()
        self._logger.info(f"{self._prefix}: Stopping")
