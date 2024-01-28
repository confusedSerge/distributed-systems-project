import os

from ipaddress import IPv4Address

from multiprocessing import Process, Event as ProcessEvent
from multiprocessing.synchronize import Event

from logging import Logger

# === Custom Modules ===

from communication import Multicast, MessageSchema, MessagePeersAnnouncement
from model import Auction, AuctionPeersStore
from util import create_logger

from constant import (
    communication as com,
    TIMEOUT_RECEIVE,
    BUFFER_SIZE,
    MULTICAST_AUCTION_PORT,
)


class AuctionPeersListener(Process):
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
        super(AuctionPeersListener, self).__init__()
        self._exit: Event = ProcessEvent()

        self._name: str = f"AuctionPeersListener::{auction.get_id()}::{os.getpid()}"
        self._logger: Logger = create_logger(self._name.lower())

        self._auction: Auction = auction
        self._store: AuctionPeersStore = auction_peers_store
        self._change: Event = change
        self._seen_message_ids: list[str] = []

        self._logger.info(f"{self._name}: Initialized")

    def run(self) -> None:
        """Runs the auction listener process

        Listens for peers announcements on the auction multicast group.
        The peers are stored in the auction peers store.

        """
        self._logger.info(f"{self._name}: Started")
        mc: Multicast = Multicast(
            group=self._auction.get_group(),
            port=MULTICAST_AUCTION_PORT,
            timeout=TIMEOUT_RECEIVE,
        )

        self._logger.info(
            f"{self._name}: Listening for peers announcements on {(self._auction.get_group(), MULTICAST_AUCTION_PORT)} for auction {self._auction.get_id()}"
        )
        while not self._exit.is_set():
            # Receive announcement or timeout to check exit condition
            try:
                message, _ = mc.receive(BUFFER_SIZE)
            except TimeoutError:
                continue

            # Ignore if message is not a peers announcement or if the message has already been seen
            if (
                not MessageSchema.of(com.HEADER_PEERS_ANNOUNCEMENT, message)
                or MessageSchema.get_id(message) in self._seen_message_ids
            ):
                continue

            # Decode message and store peers
            peers_announcement: MessagePeersAnnouncement = (
                MessagePeersAnnouncement.decode(message)
            )

            self._logger.info(
                f"{self._name}: Received peers announcement {peers_announcement}"
            )
            self._seen_message_ids.append(peers_announcement._id)
            changes: bool = self._store.replace(
                [(IPv4Address(peer[0]), peer[1]) for peer in peers_announcement.peers]
            )

            # Set change event if changes were made
            if not changes:
                continue

            self._logger.info(
                f"{self._name}: Peers announcement caused changes in the store"
            )
            self._change.set()

        self._logger.info(f"{self._name}: Releasing resources")
        mc.close()

        self._logger.info(f"{self._name}: Stopped")

    def stop(self) -> None:
        """Stops the auction listener process."""
        self._exit.set()
        self._logger.info(f"{self._name}: Stopping")
