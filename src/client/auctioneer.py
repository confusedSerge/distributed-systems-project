import multiprocessing
from multiprocessing.managers import BaseManager
import uuid

import re
import inquirer

from model import Auction

from util.helper import create_logger, logging
from util import Multicast, Unicast, find_replicas, listen_auction, message as msgs
from constant import communication as addr, interaction as inter, state as auction_state


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

        self.auctions: dict[str, Auction] = {}
        self.sub_auctioneers: dict[str, multiprocessing.Process] = {}

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

        for sub_auctioneer in self.sub_auctioneers.values():
            sub_auctioneer.terminate()

        self.manager_running.clear()

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
            print(f"* {auction}")
        print()

    def _create_auction(self) -> None:
        """Creates an auction.

        This reads in the item, price and time from the user and instantiates a sub-auctioneer.
        """
        item, price, time = self._define_auction_item()
        _uuid: str = str(uuid.uuid4())  # TODO: Generate a global unique id

        if not self.manager_running.is_set():
            self.logger.error(
                "Manager is not running, cannot create auction. This should not happen."
            )
        self.auctions[_uuid] = self.manager.Auction(item, price, time, _uuid)

        sub_auctioneer = _SubAuctioneer(self.auctions[_uuid], self.config)
        sub_auctioneer.start()

        # Store sub-auctioneer in dictionary corresponding to auction id
        self.sub_auctioneers[_uuid] = sub_auctioneer

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
    """Sub-Auctioneer class handles the auctioning of items, keeping track of the highest bid and announcing the winner."""

    def __init__(self, auction: Auction, config: dict) -> None:
        """Initializes the sub-auctioneer class.

        Args:
            config (dict): The configuration of the sub-auctioneer.
        """
        super().__init__()

        self.name = f"Sub-Auctioneer-{auction.get_id()}"

        self.logger: logging.Logger = create_logger(self.name.lower())
        self.config: dict = config

        self._auction: Auction = auction

    def run(self) -> None:
        """Runs the sub-auctioneer.

        Args:
            auction (Auction): The auction to run.
        """
        replica_list = []

        self.logger.info(f"{self.name} for auction {self._auction} is finding replicas")
        find_replicas(self._auction, replica_list, 3)
        self.logger.info(
            f"{self.name} for auction {self._auction} found replicas, releasing replica list"
        )

        # create multicast sender to send replica list
        auction_group, auction_port = self._auction.get_multicast_group_port()
        mc_sender = Multicast(auction_group, auction_port)
        replica_list_message = msgs.AuctionReplicaPeers(
            _id=self._auction.get_id(), replicas=replica_list
        )
        mc_sender.send(replica_list_message.encode())

        # Announce auction
        self.logger.info(
            f"{self.name} for auction {self._auction} is announcing auction"
        )
        mc_sender = Multicast(addr.MULTICAST_GROUP, addr.MULTICAST_PORT)
        announcement = msgs.AuctionAnnouncement(
            _id=self._auction.get_id(),
            item=self._auction.get_item(),
            price=self._auction.get_price(),
            time=self._auction.get_time(),
            multicast_group=auction_group,
            multicast_port=auction_port,
        )
        mc_sender.send(announcement.encode())
        self._auction.next_state()

        # Create multicast listener to receive bids and update auction state
        listen_auction(self._auction)

    def stop(self) -> None:
        """Stops the sub-auctioneer."""
        pass


class _AuctionManager(BaseManager):
    pass
