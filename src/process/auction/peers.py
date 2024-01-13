import os

from multiprocessing import Process, Event

from communication import Multicast, MessageSchema, MessagePeersAnnouncement

from model import Auction, AuctionPeersStore
from constant import (
    communication as com,
    TIMEOUT_RECEIVE,
    BUFFER_SIZE,
    MULTICAST_AUCTION_PORT,
    USERNAME,
)

from util import create_logger, logger


class AuctionPeersListener(Process):
    """Auction replica peers listener process.

    This process listens the peers announcement on the auction multicast group.
    """

    def __init__(self, auction: Auction, auction_peers_store: AuctionPeersStore):
        """Initializes the auction listener process.

        Args:
            auction_id (str): The auction id of the auction to listen to.
            address (str): The address of the auction to listen to.
            auction_peers_store (AuctionPeersStore): The auction peers store to listen to. Should be a shared memory object.
        """
        super(AuctionPeersListener, self).__init__()
        self._exit: Event = Event()

        self._name: str = f"AuctionPeersListener::{USERNAME}::{os.getpid()}"
        self._logger: logger = create_logger(self._name.lower())

        self._auction: Auction = auction
        self._store: AuctionPeersStore = auction_peers_store

    def run(self) -> None:
        """Runs the auction listener process."""
        self._logger.info(f"{self._name} is starting background tasks")
        mc = Multicast(
            group=self._auction.get_address(),
            port=MULTICAST_AUCTION_PORT,
            timeout=TIMEOUT_RECEIVE,
        )

        while not self._exit.is_set():
            # Receive announcement
            try:
                peers, _ = mc.receive(BUFFER_SIZE)
            except TimeoutError:
                continue

            if not MessageSchema.of(com.HEADER_PEERS_ANNOUNCEMENT, peers):
                continue

            peers: MessagePeersAnnouncement = MessagePeersAnnouncement.decode(peers)

            if Auction.parse_id(peers._id) != self._auction.get_id():
                continue

            self._store.replace(peers.peers)
            self._logger.info(f"{self._name} updated peers store")

        self._logger.info(f"{self._name} received stop signal; releasing resources")
        mc.close()

        self._logger.info(f"{self._name} stopped listening to auction announcements")

    def stop(self) -> None:
        """Stops the auction listener process."""
        self._logger.info(f"{self._name} received stop signal")
        self._exit.set()
