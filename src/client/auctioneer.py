import os

from ipaddress import IPv4Address

from multiprocessing import Process, Event as ProcessEvent
from multiprocessing.synchronize import Event
from time import sleep, time

from logging import Logger

import re
import inquirer
from communication.messages.auction.auction_announcement import (
    MessageAuctionAnnouncement,
)

# === Custom Modules ===

from model import Auction, AuctionAnnouncementStore, AuctionPeersStore
from process import Manager, ReplicationManager, AuctionBidListener
from communication import Multicast, AuctionMessageData

from util import create_logger, generate_mc_group, generate_message_id

from constant import (
    interaction as inter,
    USERNAME,
    SLEEP_TIME,
    REPLICA_EMITTER_PERIOD,
    REPLICA_AUCTION_POOL_SIZE,
    MULTICAST_DISCOVERY_GROUP,
    MULTICAST_DISCOVERY_PORT,
)


class Auctioneer:
    """Auctioneer class handles the auctioning of items, keeping track of the highest bid and announcing the winner.

    Auctioneer is run in client thread delegates its background tasks (listeners) to other processes, sharing the same memory.

    The auctioneer class is responsible for the following:
    - Creating an auction: The auctioneer creates an auction by defining the item, price and time and starting the auction (delegating to sub-auctioneer).
    - List all auctions: The auctioneer lists all auctions currently running by the auctioneer.
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
        self._name: str = self.__class__.__name__.lower()
        self._prefix: str = f"{self._name}"
        self._logger: Logger = create_logger(self._name.lower())

        # Shared memory
        self.manager: Manager = manager
        self.manager_running: Event = manager_running

        self.auction_announcement_store: AuctionAnnouncementStore = (
            auction_announcement_store
        )

        # Keep track of created auctions and corresponding sub-auctioneers
        self._created_auctions: dict[str, Auction] = {}
        self._sub_auctioneers: dict[str, _SubAuctioneer] = {}

        self._logger.info(f"{self._name}: Initialized")

    def stop(self) -> None:
        """Stops the auctioneer background tasks."""
        self._logger.info(f"{self._name}: Releasing resources")

        for sub_auctioneer in self._sub_auctioneers.values():
            sub_auctioneer.stop()

        for sub_auctioneer in self._sub_auctioneers.values():
            sub_auctioneer.join()

        self._logger.info(f"{self._name}: Stopped")

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

    # === Interaction methods ===

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
        assert self.manager_running.is_set()

        # Prompt user for auction information
        self._logger.info(f"{self._name}: Creating auction")
        aname, item, price, running_time = self._define_auction()
        if aname is None or item is None or price is None or running_time is None:
            return

        # calculate end time
        end_time = time() + running_time

        # Create auction
        address: IPv4Address = generate_mc_group(
            self.auction_announcement_store.get_groups()
        )
        _auction: Auction = self.manager.Auction(  # type: ignore
            aname, USERNAME, item, price, end_time, address
        )
        self._logger.info(f"{self._name}: Created auction {_auction}")

        # Start sub-auctioneer
        sub_auctioneer = _SubAuctioneer(_auction, self.manager)
        sub_auctioneer.start()
        self._logger.info(
            f"{self._name}: Started sub-auctioneer for auction {_auction}"
        )

        self._created_auctions[_auction.get_id()] = _auction
        self._sub_auctioneers[_auction.get_id()] = sub_auctioneer

    # === Prompt Methods ===

    def _define_auction(
        self,
    ) -> tuple[str | None, str | None, float | None, int | None]:
        """Defines the item of the auction.

        Returns:
            tuple[str, str, float, int]: The name, item, price and time of the auction.
        """
        answer = inquirer.prompt(
            [
                inquirer.Text(
                    "name",
                    message="What's the name of the auction",
                    validate=lambda _, x: len(x) > 0
                    and Auction.id(USERNAME, x) not in self._created_auctions.keys(),
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

        if (
            answer is None
            or not all(map(lambda x: x is not None, answer.values()))
            or not [x in answer.keys() for x in ["name", "item", "price", "time"]]
        ):
            print("Invalid Auction definition")
            return (None, None, None, None)

        return (
            answer["name"] if "name" in answer else None,
            answer["item"] if "item" in answer else None,
            float(answer["price"]) if "price" in answer else None,
            int(answer["time"]) if "time" in answer else None,
        )


class _SubAuctioneer(Process):
    """Sub-Auctioneer class handles the creation of auctions, replicating the auction to other auctioneers and listening to bids.

    The sub-auctioneer does not handle the auctioning of items, keeping track of the highest bid and announcing the winner.
    This is handled by the replicas of the auction. The sub-auctioneer is responsible for the following:
    - Replicating the auction: The sub-auctioneer replicates the auction to replicas that will run the auction.
    - Announcing the auction: The sub-auctioneer announces the auction to others.
    - Listening to bids: The sub-auctioneer listens to bids for the auction and updates the local auction state.
    """

    def __init__(self, auction: Auction, manager: Manager) -> None:
        """Initializes the sub-auctioneer class.

        Args:
            auction (Auction): The auction to run. Should be a shared memory object.
            manager (Manager): The manager to use for shared memory.
        """
        super(_SubAuctioneer, self).__init__()
        self._exit: Event = ProcessEvent()

        self._name: str = self.__class__.__name__.lower()
        self._prefix: str = f"{self._name}::{auction.get_id()}"
        self._logger: Logger = create_logger(self._name, with_pid=True)

        # Shared memory
        self._auction: Auction = auction
        self._manager: Manager = manager

        self._logger.info(
            f"{self._name}: Initialized for auction {auction} on {auction.get_group()}"
        )

    def run(self) -> None:
        """Runs the sub-auctioneer.

        Args:
            auction (Auction): The auction to run.
        """
        self._logger.info(f"{self._name}: Started")
        self._replicate()

        if self._exit.is_set():
            self._logger.info(f"{self._name}: Exiting as process received stop signal")
            return

        # Create multicast listener to receive bids and update auction state
        self._listen()

        self._logger.info(f"{self._name}: Finished")

    def stop(self) -> None:
        """Stops the sub-auctioneer."""
        self._logger.info(f"{self._name}: Stop signal received")
        self._exit.set()

    # === Helper methods ===

    def _auction_preparation(self) -> None:
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
        self._logger.info(f"{self._prefix}: Announced auction {self._auction.get_id()}")

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
            self._auction, replica_list, REPLICA_EMITTER_PERIOD
        )
        replica_finder.start()
        replica_finder.join()

        # Check if enough replicas were found
        if replica_list.len() < REPLICA_AUCTION_POOL_SIZE:
            self._logger.info(
                f"{self._name}: Not enough replicas found, cancelling auction {self._auction.get_id()}"
            )
            self._auction.cancel()
            self._exit.set()
            return

        self._logger.info(
            f"{self._name}: Replicated auction {self._auction.get_id()} to replicas {replica_list.str()}"
        )

    def _listen(self):
        """Starts the auction bid listener to listen to bids for the auction."""
        self._logger.info(
            f"{self._name}: Listening to bids for auction {self._auction.get_id()}"
        )
        auction_bid_listener: AuctionBidListener = AuctionBidListener(self._auction)
        auction_bid_listener.start()

        # Wait for auction to end or if stop signal is received propagate stop signal and return
        while not self._exit.is_set() and auction_bid_listener.is_alive():
            sleep(SLEEP_TIME)

        if self._exit.is_set():
            auction_bid_listener.stop()
            self._logger.info(
                f"{self._name}: Stop signal received, stopping auction bid listener"
            )
            auction_bid_listener.join()
