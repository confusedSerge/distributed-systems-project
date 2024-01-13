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

        self._name: str = f"AuctionPeersListener::{auction.get_id()}::{os.getpid()}"
        self._logger: logger = create_logger(self._name.lower())

        self._auction: Auction = auction
        self._seen_mid: list[str] = []
        self._store: AuctionPeersStore = auction_peers_store

        self._logger.info(f"{self._name}: Initialized")

    def run(self) -> None:
        """Runs the auction listener process."""
        self._logger.info(f"{self._name}: Started")
        mc = Multicast(
            group=self._auction.get_address(),
            port=MULTICAST_AUCTION_PORT,
            timeout=TIMEOUT_RECEIVE,
        )

        self._logger.info(
            f"{self._name}: Listening for peers announcements on {(self._auction.get_address(), MULTICAST_AUCTION_PORT)} for auction {self._auction.get_id()}"
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
            if peers._id in self._seen_mid:
                self._logger.info(
                    f"{self._name}: Received duplicate peers announcement {peers}"
                )
                continue

            try:
                if Auction.parse_id(peers._id) != self._auction.get_id():
                    self._logger.info(
                        f"{self._name}: Received peers announcement {peers} for auction {Auction.parse_id(peers._id)}"
                    )
                    continue
            except ValueError:
                self._logger.warning(
                    f"{self._name}: Received peers announcement {peers} with invalid auction id {peers._id}"
                )
                continue

            self._logger.info(f"{self._name}: Received peers announcement {peers}")
            self._seen_mid.append(peers._id)
            self._store.replace(peers.peers)

        self._logger.info(f"{self._name}: Releasing resources")
        mc.close()

        self._logger.info(f"{self._name}: Stopped")

    def stop(self) -> None:
        """Stops the auction listener process."""
        self._exit.set()
        self._logger.info(f"{self._name}: Stopping")
