from ipaddress import IPv4Address

from multiprocessing import Process, Event
from time import sleep

import re
import inquirer

from model import Auction, AuctionAnnouncementStore, AuctionPeersStore
from process import Manager, ReplicaFinder, AuctionBidListener

from communication import (
    Multicast,
    AuctionMessageData,
    MessageAuctionAnnouncement,
)


from util import create_logger, logging, gen_mcadd, gen_mid

from constant import (
    interaction as inter,
    USERNAME,
    SLEEP_TIME,
    EMMITER_PERIOD,
    REPLICA_AUCTION_POOL_SIZE,
    MULTICAST_DISCOVERY_GROUP,
    MULTICAST_DISCOVERY_PORT,
    MULTICAST_DISCOVERY_TTL,
)


class Auctioneer:
    """Auctioneer class handles the auctioning of items, keeping track of the highest bid and announcing the winner.

    Auctioneer is run in client thread delegates its background tasks (listeners) to other processes, sharing the same memory.

    The auctioneer class is responsible for the following:
    - Creating an auction: The auctioneer creates an auction by defining the item, price and time and starting the auction (delegating to sub-auctioneer).
    - List all auctions: The auctioneer lists all auctions currently running.
    - Information about an auction: The auctioneer lists information about a specific auction.
    """

    def __init__(
        self,
        manager: Manager,
        manager_running: Event,
        auction_announcement_store: AuctionAnnouncementStore,
    ) -> None:
        """Initializes the auctioneer class.

        Args:
            manager (Manager): The manager to use for shared memory.
            manager_running (Event): The event to use to check if the manager is running.
            auction_announcement_store (AuctionAnnouncementStore): The auction announcement store to store the auction announcements in. Should be a shared memory object.
        """
        self._name: str = "Auctioneer"
        self._logger: logging.Logger = create_logger(self._name.lower())

        # Shared memory
        self.manager: Manager = manager
        self.manager_running: Event = manager_running

        self.auction_announcement_store: AuctionAnnouncementStore = (
            auction_announcement_store
        )

        self._created_auctions: dict[str, Auction] = {}
        self._sub_auctioneers: list[_SubAuctioneer] = []

        self._logger.info(f"{self._name} initialized")

    def stop(self) -> None:
        """Stops the auctioneer background tasks."""
        self._logger.info(f"{self._name} received stop signal")

        # No graceful shutdown needed, terminate all listeners
        for sub_auctioneer in self._sub_auctioneers:
            sub_auctioneer.stop()

        for sub_auctioneer in self._sub_auctioneers:
            sub_auctioneer.join()

        self._logger.info(f"{self._name} stopped sub-auctioneers")

    def interact(self) -> None:
        """Handles the interactive command line interface for the auctioneer.

        This should be run in the main thread (process), handling user input.
        """
        while True:
            answer = inquirer.prompt(
                [
                    inquirer.List(
                        "action",
                        message=inter.AUCTIONEER_ACTION_QUESTION,
                        choices=[
                            inter.AUCTIONEER_ACTION_START,
                            inter.AUCTIONEER_ACTION_LIST_OWN_AUCTIONS,
                            inter.AUCTIONEER_ACTION_GO_BACK,
                        ],
                    )
                ]
            )

            if answer is None:
                break

            match answer["action"]:
                case inter.AUCTIONEER_ACTION_START:
                    self._create_auction()
                case inter.AUCTIONEER_ACTION_LIST_OWN_AUCTIONS:
                    self._list_auctions()
                case inter.AUCTIONEER_ACTION_GO_BACK:
                    break
                case _:
                    self._logger.error(f"Invalid action {answer['action']}")

    def _list_auctions(self) -> None:
        """Lists all auctions."""
        print("Your auctions:")
        for auction in self._created_auctions.values():
            print(f"* {auction}")
        print()

    def _create_auction(self) -> None:
        """Creates an auction.

        This reads in the item, price and time from the user and instantiates a sub-auctioneer.
        """
        self._logger.info(f"{self._name} is creating an auction")
        if not self.manager_running.is_set():
            self._logger.error(
                "Manager is not running, cannot create auction. This should not happen."
            )
            return

        aname, item, price, time = self._define_auction()
        address: IPv4Address = gen_mcadd(
            self.auction_announcement_store.get_addresses()
        )
        _auction: Auction = self.manager.Auction(
            aname, USERNAME, item, price, time, address
        )

        self._created_auctions[_auction.get_id()] = _auction
        self._logger.info(f"{self._name} created auction {_auction.get_id()}")

        sub_auctioneer = _SubAuctioneer(_auction, self.manager)
        sub_auctioneer.start()
        self._sub_auctioneers.append(sub_auctioneer)

    def _define_auction(self) -> tuple[str, str, float, int]:
        """Defines the item of the auction.

        Returns:
            tuple[str, str, float, int]: The name, item, price and time of the auction.
        """
        answer: dict = inquirer.prompt(
            [
                inquirer.Text(
                    "name",
                    message="What's the name of the auction",
                    validate=lambda _, x: len(x) > 0
                    and Auction.id(x, USERNAME) not in self._created_auctions.keys(),
                ),
                inquirer.Text(
                    "item", message="What's the item", validate=lambda _, x: len(x) > 0
                ),
                inquirer.Text(
                    "price",
                    message="What's the starting price",
                    validate=lambda _, x: re.match(r"^\d+(\.\d{1,2})?$", x) is not None,
                    default="0.00",
                ),
                inquirer.Text(
                    "time",
                    message="How long should the auction last (in seconds)",
                    validate=lambda _, x: re.match(r"^\d+$", x) is not None,
                    default="60",
                ),
            ]
        )
        return (
            answer["name"],
            answer["item"],
            float(answer["price"]),
            int(answer["time"]),
        )


class _SubAuctioneer(Process):
    """Sub-Auctioneer class handles the auctioning of items, keeping track of the highest bid and announcing the winner."""

    def __init__(self, auction: Auction, manager: Manager) -> None:
        """Initializes the sub-auctioneer class.

        Args:
            auction (Auction): The auction to run. Should be a shared memory object.
            manager (Manager): The manager to use for shared memory.
        """
        super(_SubAuctioneer, self).__init__()
        self._exit = Event()

        self._name = f"SubAuctioneer::{auction.get_id()}"
        self._logger: logging.Logger = create_logger(self._name.lower())

        self._auction: Auction = auction
        self._manager: Manager = manager

        self._logger.info(f"{self._name} initialized")

    def run(self) -> None:
        """Runs the sub-auctioneer.

        Args:
            auction (Auction): The auction to run.
        """
        self._logger.info(f"{self._name} is starting background task")
        self._replicate()

        if self._exit.is_set():
            return

        # Announce auction
        self._announce()

        # Create multicast listener to receive bids and update auction state
        self._listen()

        if self._exit.is_set():
            return

        self._logger.info(
            f"{self._name} for auction {self._auction.get_id()} stopped listening to bids as auction ended"
        )

    def _announce(self):
        self._logger.info(
            f"{self._name} for auction {self._auction.get_id()} is announcing auction"
        )
        announcement: MessageAuctionAnnouncement = MessageAuctionAnnouncement(
            _id=gen_mid(self._auction.get_id()),
            auction=AuctionMessageData.from_auction(self._auction),
        )
        Multicast.qsend(
            message=announcement.encode(),
            group=MULTICAST_DISCOVERY_GROUP,
            port=MULTICAST_DISCOVERY_PORT,
            ttl=MULTICAST_DISCOVERY_TTL,
        )
        self._auction.next_state()

    def stop(self) -> None:
        """Stops the sub-auctioneer."""
        self._logger.info(f"{self._name} received stop signal")
        self._exit.set()

    def _replicate(self) -> None:
        """Replicates the auction to the other auctioneers."""

        self._logger.info(
            f"{self._name} for auction {self._auction.get_id()} is finding replicas"
        )
        replica_list: AuctionPeersStore = self._manager.AuctionPeersStore()
        replica_finder: ReplicaFinder = ReplicaFinder(
            self._auction, replica_list, EMMITER_PERIOD
        )
        replica_finder.start()
        replica_finder.join()

        if replica_list.len() < REPLICA_AUCTION_POOL_SIZE:
            self._logger.info(
                f"{self._name} for auction {self._auction.get_id()} found not enough replicas, cancelling auction"
            )
            self._auction.cancel()
            self._exit.set()
            return

        self._logger.info(
            f"{self._name} for auction {self._auction.get_id()} found replicas, releasing replica list"
        )

    def _listen(self):
        """Listens to bids for the auction."""
        self._logger.info(
            f"{self._name} for auction {self._auction.get_id()} is listening to bids"
        )
        auction_bid_listener: AuctionBidListener = AuctionBidListener(self._auction)
        auction_bid_listener.start()

        # Wait for auction to end or if stop signal is received propegate stop signal and return
        while not self._exit.is_set() and auction_bid_listener.is_alive():
            sleep(SLEEP_TIME)

        if self._exit.is_set():
            auction_bid_listener.stop()
            self._logger.info(
                f"{self._name} stopped listening to bids as process received stop signal"
            )
            auction_bid_listener.join()
