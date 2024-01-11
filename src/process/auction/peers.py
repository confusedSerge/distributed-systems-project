import os

from multiprocessing import Process, Event

from communication import Unicast, MessageSchema, MessagePeersAnnouncement

from model import Auction, AuctionPeersStore
from constant import header as hdr, TIMEOUT_RECEIVE, BUFFER_SIZE, UNICAST_PORT

from util import create_logger, logger


class AuctionPeersListener(Process):
    """Auction replica peers listener process.

    This process listens the peers announcement on the unicast channel.
    """

    def __init__(self, auction_id: str, auction_peers_store: AuctionPeersStore):
        """Initializes the auction listener process.

        Args:
            auction_id (str): The auction id of the auction to listen to.
            auction_peers_store (AuctionPeersStore): The auction peers store to listen to. Should be a shared memory object.
        """
        super(AuctionPeersListener, self).__init__()
        self._exit: Event = Event()

        self._name: str = f"AuctionPeersListener-{os.getpid()}"
        self._logger: logger = create_logger(self._name.lower())

        self._auction_id: str = auction_id
        self._store: AuctionPeersStore = auction_peers_store

    def run(self) -> None:
        """Runs the auction listener process."""
        self._logger.info(f"{self._name} is starting background tasks")
        uc: Unicast = Unicast(host=None, port=UNICAST_PORT, timeout=TIMEOUT_RECEIVE)

        while not self._exit.is_set():
            # Receive announcement
            try:
                peers, _ = uc.receive(BUFFER_SIZE)
            except TimeoutError:
                continue

            if not MessageSchema.of(hdr.PEERS_ANNOUNCEMENT, peers):
                continue

            peers: MessagePeersAnnouncement = MessagePeersAnnouncement.decode(peers)

            if Auction.parse_id(peers._id) != self._auction_id:
                continue

            self._store.replace(peers.peers)

        self._logger.info(f"{self._name} received stop signal; releasing resources")
        uc.close()

        self._logger.info(f"{self._name} stopped listening to auction announcements")

    def stop(self) -> None:
        """Stops the auction listener process."""
        self._logger.info(f"{self._name} received stop signal")
        self._exit.set()
