import multiprocessing
from multiprocessing import Manager
from multiprocessing.managers import BaseManager

import inquirer

from model.auction import Auction
from util.message import AuctionAnnouncement
from util.helper import create_logger, logging
from constant import interaction as inter


class Bidder:
    """The bidder class handles the bidding process of the client.

    Bidder is run in the main thread (process) of the client and delegates its background tasks (listeners) to other processes, sharing the same memory.

    The bidder class is responsible for the following:
    - Joining as a bidder: The bidder sends a discovery message to the multicast group to find auctions and keeps listening for auction announcements (background process for listening).
    - Joining an auction: The bidder joins the auction by joining the multicast group of the auction
        and starts listening for messages from the auction, keeping track of the highest bid and announcements of the winner.
    - Bidding: The bidder sends a bid to the auction by sending a message to the multicast group of the auction containing the bid.
    - Leaving an auction: The bidder leaves the auction by leaving the multicast group of the auction, and stops listening for messages from the auction.
    - Leaving as a bidder: The bidder leaves the multicast group, stops listening for auction announcements and clears the list of auctions.
    """

    def __init__(self, config: dict) -> None:
        """Initializes the bidder class

        Args:
            config (dict): The configuration of the bidder.
        """
        self.name = "Bidder"

        self.logger: logging.Logger = create_logger(self.name.lower())
        self.config: dict = config

        self.background: multiprocessing.Process = None

        # Shared memory
        _AuctionManager.register("_AuctionAnnouncementStore", _AuctionAnnouncementStore)
        _AuctionManager.register("Auction", Auction)

        self.manager: _AuctionManager = _AuctionManager()
        self._auction_announcement_store: _AuctionAnnouncementStore = None
        self._joined_auctions: dict[str, Auction] = {}

    def start(self) -> None:
        """Starts the bidder background tasks."""
        self.logger.info(f"{self.name} is starting background tasks")

        self.background = multiprocessing.Process(target=self._background)

        self.manager.start()
        self._auction_announcement_store = self.manager._AuctionAnnouncementStore()

        self.logger.info(f"{self.name} started background tasks")

    def _background(self) -> None:
        """Runs the bidder background tasks."""
        pass

    def stop(self) -> None:
        """Stops the bidder background tasks."""
        self.logger.info(f"{self.name} is stopping background tasks")

        if self.background is not None and self.background.is_alive():
            self.background.terminate()

        self.logger.info(f"{self.name} stopped background tasks")

    def interact(self) -> None:
        """Handles the interactive command line interface for the bidder.

        This should be run in the main thread (process), handling user input.
        """
        while True:
            answer = inquirer.prompt(
                [
                    inquirer.List(
                        "action",
                        message=inter.BIDDER_ACTION_QUESTION,
                        choices=[
                            inter.BIDDER_ACTION_LIST_AUCTIONS,
                            inter.BIDDER_ACTION_JOIN_AUCTION,
                            inter.BIDDER_ACTION_LEAVE_AUCTION,
                            inter.BIDDER_ACTION_BID,
                            inter.BIDDER_ACTION_GO_BACK,
                        ],
                    )
                ]
            )

            match answer["action"]:
                case inter.BIDDER_ACTION_LIST_AUCTIONS:
                    self._list_auctions()
                case inter.BIDDER_ACTION_JOIN_AUCTION:
                    self._join_auction()
                case inter.BIDDER_ACTION_LEAVE_AUCTION:
                    self._leave_auction()
                case inter.BIDDER_ACTION_BID:
                    self._bid()
                case inter.BIDDER_ACTION_GO_BACK:
                    break
                case _:
                    self.logger.error(f"Invalid action {answer['action']}")

    def _list_auctions(self) -> None:
        """Lists the auctions available to join."""
        print("Auctions available to join:")
        for auction_id, auction in self._auction_announcement_store.items():
            print(f"* {auction_id}: {auction}")

    def _join_auction(self) -> None:
        """Joins an auction"""
        auction_id = self._choose_auction(list(self._auction_announcement_store.keys()))
        if auction_id in self._joined_auctions:
            print("You have already joined this auction")
            return

        # TODO: Implement joining of auction (server needed) -> create auction listener and start it

    def _leave_auction(self) -> None:
        """Leaves an auction"""
        auction_id = self._choose_auction(list(self._joined_auctions.keys()))
        # TODO: Implement leaving of auction (server needed) -> call stop() on auction listener

    def _bid(self) -> None:
        """Bids in an auction"""
        auction_id = self._choose_auction(list(self._joined_auctions.keys()))
        # TODO: Implement bidding in auction (server needed) -> call bid() on auction listener

    def _choose_auction(self, auction_ids: list[int]) -> int:
        """Chooses an auction.

        Prompts the user to choose an auction and returns the auction id.

        Args:
            auction_ids (list[int]): The auction ids of the auctions to choose from.

        Returns:
            int: The auction id of the auction.
        """
        return int(
            inquirer.prompt(
                [
                    inquirer.List(
                        "auction_id",
                        message=inter.BIDDER_CHOOSE_AUCTION_QUESTION,
                        choices=list(map(str, auction_ids)),
                    )
                ]
            )["auction_id"]
        )


class _AuctionManager(BaseManager):
    pass


class _AuctionAnnouncementStore:
    """The auction announcement store class stores auction announcements.

    This is used by the bidder to keep track of auctions.
    """

    def __init__(self) -> None:
        self._auctions: dict[int, AuctionAnnouncement] = {}

    def add(self, auction: AuctionAnnouncement) -> None:
        """Adds an auction announcement to the store.

        Args:
            auction (AuctionAnnouncement): The auction announcement to add.
        """
        if self.exists(auction._id):
            raise ValueError(f"Auction with id {auction._id} already exists")
        self._auctions[auction._id] = auction

    def get(self, auction_id: int) -> AuctionAnnouncement:
        """Returns an auction announcement from the store.

        Args:
            auction_id (int): The auction id of the auction announcement to get.

        Returns:
            AuctionAnnouncement: The auction announcement.
        """
        if not self.exists(auction_id):
            raise ValueError(f"Auction with id {auction_id} does not exist")
        return self._auctions[auction_id]

    def remove(self, auction_id: int) -> None:
        """Removes an auction announcement from the store.

        Args:
            auction_id (int): The auction id of the auction announcement to remove.
        """
        if not self.exists(auction_id):
            raise ValueError(f"Auction with id {auction_id} does not exist")
        del self._auctions[auction_id]

    def items(self) -> list[tuple[int, AuctionAnnouncement]]:
        """Returns the items of the store.

        Returns:
            list[tuple[int, AuctionAnnouncement]]: The items of the store.
        """
        return self._auctions.items()

    def exists(self, auction_id: int) -> bool:
        """Returns whether an auction announcement exists in the store.

        Args:
            auction_id (int): The auction id of the auction announcement to check.

        Returns:
            bool: Whether the auction announcement exists in the store.
        """
        return auction_id in self._auctions
