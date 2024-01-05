import multiprocessing
from multiprocessing.managers import BaseManager
import uuid

import re
import inquirer

from model import Auction

from util.helper import create_logger, logging
from constant import interaction as inter


class Auctioneer:
    """Auctioneer class handles the auctioning of items, keeping track of the highest bid and announcing the winner.

    Auctioneer is run in main thread (process) of the client and delegates its background tasks (listeners) to other processes, sharing the same memory.

    The auctioneer class is responsible for the following:
    - Creating an auction: The auctioneer creates an auction by defining the item, price and time and starting the auction (delegating to sub-auctioneer).
    - List all auctions: The auctioneer lists all auctions currently running.
    - Information about an auction: The auctioneer lists information about a specific auction.
    """

    def __init__(self, config: dict) -> None:
        """Initializes the auctioneer class.

        Args:
            config (dict): The configuration of the auctioneer.
        """
        self.name = "Auctioneer"

        self.logger: logging.Logger = create_logger(self.name.lower())
        self.config: dict = config

        self.background: multiprocessing.Process = None

        # Shared memory
        _AuctionManager.register("Auction", Auction)

        self.manager_running = multiprocessing.Event()
        self.manager: _AuctionManager = _AuctionManager()
        self.auctions: dict[int, Auction] = {}

    def start(self) -> None:
        """Starts the auctioneer background tasks."""
        self.logger.info(f"{self.name} is starting background tasks")

        self.background = multiprocessing.Process(target=self._background)
        self.manager.start()
        self.manager_running.set()

        self.logger.info(f"{self.name} started background tasks")

    def _background(self) -> None:
        """Runs the auctioneer background tasks."""
        pass

    def stop(self) -> None:
        """Stops the auctioneer background tasks."""
        self.logger.info(f"{self.name} is stopping background tasks")

        if self.background is not None and self.background.is_alive():
            self.background.terminate()

        self.logger.info(f"{self.name} stopped background tasks")

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

            match answer["action"]:
                case inter.AUCTIONEER_ACTION_START:
                    self._create_auction()
                case inter.AUCTIONEER_ACTION_LIST_OWN_AUCTIONS:
                    self._list_auctions()
                case inter.AUCTIONEER_ACTION_GO_BACK:
                    break
                case _:
                    self.logger.error(f"Invalid action {answer['action']}")

    def _list_auctions(self) -> None:
        """Lists all auctions."""
        print("Your auctions:")
        for auction in self.auctions.values():
            print(f"\t* {auction}")
        print()

    def _create_auction(self) -> None:
        """Creates an auction.

        This reads in the item, price and time from the user and instantiates a sub-auctioneer.
        """
        item, price, time = self._define_auction_item()
        _uuid = uuid.uuid4().int  # TODO: Generate unique id in a better way

        if not self.manager_running.is_set():
            self.logger.error(
                "Manager is not running, cannot create auction. This should not happen."
            )
        self.auctions[uuid] = self.manager.Auction(item, price, time, _uuid)

        # TODO: Start sub-auctioneer with auction

    def _define_auction_item(self) -> tuple[str, float, int]:
        """Defines the item of the auction.

        Returns:
            tuple[str, float, int]: The item, price and time of the auction.
        """
        answer: dict = inquirer.prompt(
            [
                inquirer.Text("item", message="What's the item"),
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
        return answer["item"], float(answer["price"]), int(answer["time"])


class _SubAuctioneer(multiprocessing.Process):
    """Sub-Auctioneer class handles the auctioning of items, keeping track of the highest bid and announcing the winner.

    The sub-auctioneer is run in a separate thread (process) from the auctioneer, for each auction the client creates.
    It handles the prelude by defining the item, price and time, finding replicas
        and starting the auction by informing the replicas of other replicas and sending an announcement of the auction to the discovery group.
    If not enough replicas are found, the auction is cancelled. This is handled by a timeout.
    After the prelude, the sub-auctioneer continues to listen on the multicast group for bids and keeps track of the auction.
    When the auction is over, the sub-auctioneer leaves the multicast group.
    """

    def __init__(self, config: dict) -> None:
        pass


class _AuctionManager(BaseManager):
    pass
