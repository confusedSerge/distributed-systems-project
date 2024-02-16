from ipaddress import IPv4Address

from multiprocessing.synchronize import Event
from time import time

from time import localtime, strftime
from logging import Logger

import re
import inquirer

# === Custom Modules ===

from model import Auction, AuctionAnnouncementStore
from process import Manager, SubAuctioneer
from communication import MessageAuctionAnnouncement, AuctionMessageData

from util import create_logger, generate_mc_group

from constant import (
    interaction as inter,
    stateid2stateobj,
    USERNAME,
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

        # Keep track of created auctions and corresponding sub-auctioneers
        self.auction_announcement_store: AuctionAnnouncementStore = (
            auction_announcement_store
        )
        self._created_auctions: dict[str, Auction] = {}
        self._sub_auctioneers: dict[str, SubAuctioneer] = {}

        self._logger.info(f"{self._prefix}: Initialized")

    def stop(self) -> None:
        """Stops the auctioneer background tasks."""
        self._logger.info(f"{self._prefix}: Releasing resources")

        for sub_auctioneer in self._sub_auctioneers.values():
            sub_auctioneer.stop()

        self._logger.info(f"{self._prefix}: Stopped")

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
        for _, auction in self.auction_announcement_store.items():
            if auction.auction._id not in self._created_auctions.keys():
                continue
            auction_data: Auction = self._get_auction_from_message(auction)
            print(
                f"Auction {auction_data.get_id()}: Progress: {auction_data.get_state_description()}, Item: {auction_data.get_item()}, Highest Bid: {auction_data.get_highest_bid()}, Ends: {strftime('%a, %d %b %Y %H:%M:%S +0000', localtime(auction.auction.time))}"
            )

    def _create_auction(self) -> None:
        """Creates an auction.

        This reads in the item, price and time from the user and instantiates a sub-auctioneer.
        """
        assert self.manager_running.is_set()

        # Prompt user for auction information
        self._logger.info(f"{self._prefix}: Creating auction")
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
        self._logger.info(f"{self._prefix}: Created auction {_auction}")

        # Start sub-auctioneer
        sub_auctioneer = SubAuctioneer(
            _auction, self.auction_announcement_store, self.manager
        )
        sub_auctioneer.start()

        self._logger.info(
            f"{self._prefix}: Started sub-auctioneer for auction {_auction}"
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

    # === Helper Methods ===

    def _get_auction_from_message(self, message: MessageAuctionAnnouncement) -> Auction:
        """Handles an auction information message.

        Creates an auction from the auction information message.
        This auction is a shared memory object.

        Args:
            message (MessageAuctionInformationResponse): The auction information message.

        Returns:
            Auction: The auction created from the message.
        """
        assert self.manager_running.is_set()

        rec = AuctionMessageData.to_auction(message.auction)
        auction: Auction = self.manager.Auction(  # type: ignore
            rec.get_name(),
            rec.get_auctioneer(),
            rec.get_item(),
            rec.get_price(),
            rec.get_end_time(),
            rec.get_group(),
        )
        auction.from_other(rec)

        return auction
