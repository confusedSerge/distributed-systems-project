from multiprocessing import Process, Event as ProcessEvent
from multiprocessing.synchronize import Event
from time import sleep

from logging import Logger

# === Custom Modules ===

from model import Auction, AuctionPeersStore, AuctionAnnouncementStore
from ..memory_manager import Manager
from .replication_manager import ReplicationManager
from process import (
    AuctionBidListener,
    AuctionAnnouncementListener,
)
from communication import Multicast, AuctionMessageData, MessageAuctionAnnouncement

from util import create_logger, generate_message_id

from constant import (
    SLEEP_TIME,
    AUCTION_POOL_SIZE,
    MULTICAST_DISCOVERY_GROUP,
    MULTICAST_DISCOVERY_PORT,
    REPLICA_REPLICATION_PERIOD,
)


class SubAuctioneer(Process):
    """Sub-Auctioneer class handles the creation of auctions, replicating the auction to other auctioneers and listening to bids.

    The sub-auctioneer does not handle the auctioning of items, keeping track of the highest bid and announcing the winner.
    This is handled by the replicas of the auction. The sub-auctioneer is responsible for the following:
    - Replicating the auction: The sub-auctioneer replicates the auction to replicas that will run the auction.
    - Announcing the auction: The sub-auctioneer announces the auction to others.
    - Listening to bids: The sub-auctioneer listens to bids for the auction and updates the local auction state.
    """

    def __init__(
        self,
        auction: Auction,
        announcement_store: AuctionAnnouncementStore,
        manager: Manager,
    ) -> None:
        """Initializes the sub-auctioneer class.

        Args:
            auction (Auction): The auction to run. Should be a shared memory object.
            announcement_store (AuctionAnnouncementStore): The auction announcement store to store the auction announcements in. Should be a shared memory object.
            manager (Manager): The manager to use for shared memory.
        """
        super(SubAuctioneer, self).__init__()
        self._exit: Event = ProcessEvent()

        self._name: str = self.__class__.__name__.lower()
        self._prefix: str = f"{self._name}::{auction.get_id()}"
        self._logger: Logger = create_logger(self._name, with_pid=True)

        # Shared memory
        self._manager: Manager = manager
        self._auction: Auction = auction
        self._announcement_store = announcement_store

        self._logger.info(
            f"{self._name}: Initialized for auction {auction} on {auction.get_group()}"
        )

    def run(self) -> None:
        """Runs the sub-auctioneer.

        Args:
            auction (Auction): The auction to run.
        """
        self._logger.info(f"{self._name}: Started")

        self._announce_auction_preparation()

        self._replicate()

        if self._exit.is_set():
            self._logger.info(f"{self._name}: Exiting as process received stop signal")
            self._announce_auction_cancelled()
            return

        # Create multicast listener to receive bids and update auction state
        self._listen()

        self._logger.info(f"{self._name}: Stopped")

    def stop(self) -> None:
        """Stops the sub-auctioneer."""
        self._logger.info(f"{self._name}: Stop signal received")
        self._exit.set()

    # === Helper methods ===

    def _announce_auction_preparation(self) -> None:
        """Announces that an auction is about to start.

        This is used to reserve the auction group and announce the auction to others.
        """
        self._logger.info(f"{self._prefix}: Preparing running auction to discovery")
        Multicast.qsend(
            message=MessageAuctionAnnouncement(
                _id=generate_message_id(self._auction.get_id()),
                auction=AuctionMessageData.from_auction(self._auction),
            ).encode(),
            group=MULTICAST_DISCOVERY_GROUP,
            port=MULTICAST_DISCOVERY_PORT,
        )
        self._logger.info(
            f"{self._prefix}: Announced auction {self._auction.get_id()} preparation to discovery"
        )

    def _announce_auction_cancelled(self) -> None:
        """Announces that an auction has been cancelled."""
        self._logger.info(f"{self._prefix}: Cancelling auction")
        self._auction.cancel()
        Multicast.qsend(
            message=MessageAuctionAnnouncement(
                _id=generate_message_id(self._auction.get_id()),
                auction=AuctionMessageData.from_auction(self._auction),
            ).encode(),
            group=MULTICAST_DISCOVERY_GROUP,
            port=MULTICAST_DISCOVERY_PORT,
        )
        self._logger.info(
            f"{self._prefix}: Announced auction {self._auction.get_id()} cancelled to discovery"
        )

    def _replicate(self) -> None:
        """Starts the replica finder to replicate the auction to other replicas that will run the auction.

        If not enough replicas are found, the auction is cancelled.
        """

        self._logger.info(
            f"{self._name}: Replicating auction {self._auction.get_id()} to replicas"
        )

        # Start replica finder process to find replicas
        replica_list: AuctionPeersStore = self._manager.AuctionPeersStore()  # type: ignore
        replica_finder: ReplicationManager = ReplicationManager(
            self._auction, replica_list, REPLICA_REPLICATION_PERIOD
        )
        replica_finder.start()
        replica_finder.join()

        # Check if enough replicas were found
        if replica_list.len() < AUCTION_POOL_SIZE:
            self._logger.info(
                f"{self._name}: Not enough replicas found, cancelling auction {self._auction.get_id()}"
            )
            self._exit.set()
            return

        self._logger.info(
            f"{self._name}: Replicated auction {self._auction.get_id()} to replicas {replica_list.str()}"
        )

    def _listen(self):
        """Starts the auction bid listener to listen to bids for the auction."""
        self._logger.info(
            f"{self._name}: Listening for auction {self._auction.get_id()}"
        )

        high_freq_auction_listener: AuctionAnnouncementListener = (
            AuctionAnnouncementListener(
                self._announcement_store, self._auction.get_id()
            )
        )
        high_freq_auction_listener.start()

        # Wait for auction to end or if stop signal is received propagate stop signal and return
        while not self._exit.is_set() and not self._auction.is_ended():
            sleep(SLEEP_TIME)

        if self._exit.is_set():
            self._logger.info(f"{self._name}: Stop signal received")
        else:
            self._logger.info(f"{self._name}: Auction ended")

        high_freq_auction_listener.stop()
        high_freq_auction_listener.join()
