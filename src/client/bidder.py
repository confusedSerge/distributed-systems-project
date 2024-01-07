import multiprocessing
from multiprocessing import Manager
from multiprocessing.managers import BaseManager
import uuid

import re
import inquirer

from model.auction import Auction
from util import (
    AuctionAnnouncement,
    create_logger,
    logging,
    Multicast,
    Unicast,
    message as msgs,
)
from constant import communication as addr, interaction as inter


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

        # Shared memory
        _AuctionManager.register("_AuctionAnnouncementStore", _AuctionAnnouncementStore)
        _AuctionManager.register("Auction", Auction)

        self.manager: _AuctionManager = _AuctionManager()

        self._auction_announcement_store: _AuctionAnnouncementStore = None
        self._auction_announcement_process: multiprocessing.Process = None

        self._joined_auctions: dict[str, Auction] = {}
        self._auction_listeners: dict[str, multiprocessing.Process] = {}

    def start(self) -> None:
        """Starts the bidder background tasks."""
        self.logger.info(f"{self.name} is starting background tasks")

        self.manager.start()

        # Start auction announcement listener
        self._auction_announcement_store = self.manager._AuctionAnnouncementStore()
        self._auction_announcement_process = _AuctionAnnouncementListener(
            self._auction_announcement_store
        )
        self._auction_announcement_process.start()

        self.logger.info(f"{self.name} started background tasks")

    def stop(self) -> None:
        """Stops the bidder background tasks."""
        self.logger.info(f"{self.name} is stopping background tasks")

        if (
            self._auction_announcement_process
            and self._auction_announcement_process.is_alive()
        ):
            self._auction_announcement_process.terminate()

        for auction_listener in self._auction_listeners.values():
            if auction_listener.is_alive():
                auction_listener.terminate()

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
                            inter.BIDDER_ACTION_LIST_AUCTION_INFO,
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
                case inter.BIDDER_ACTION_LIST_AUCTION_INFO:
                    self._list_auction_info()
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

    def _list_auction_info(self) -> None:
        """Lists the information of an auction."""
        auction_id = self._choose_auction(list(self._joined_auctions.keys()))
        auction = self._joined_auctions[auction_id]
        print(f"Information about auction {auction_id}:")
        print(f"* Joined auction {auction_id}: {auction}")
        print(f"* Highest bid: {auction.get_highest_bid()}")
        print(f"* Winner: {auction.get_winner() if auction.get_winner() else 'None'}")

    def _join_auction(self) -> None:
        """Joins an auction

        TODO: Reduce complexity
        """
        not_joined_auctions: list[str] = [
            auction_id
            for auction_id in self._auction_announcement_store.keys()
            if auction_id not in self._joined_auctions
        ]
        auction_id = self._choose_auction(not_joined_auctions)

        # Request auction information by sending information request to multicast group of auction
        try:
            auction_announcement: AuctionAnnouncement = (
                self._auction_announcement_store.get(auction_id)
            )
        except ValueError as e:
            self.logger.error(f"Auction announcement with id {auction_id} not found")
            return

        mc_sender = Multicast(
            auction_announcement.get_multicast_group(),
            auction_announcement.get_multicast_port(),
        )
        unicast_listener = Unicast("", addr.UNICAST_PORT, sender=False)

        mc_sender.send(
            msgs.AuctionInformationRequest(
                _id=str(uuid.uuid4()), auction_id=auction_id
            ).encode()
        )

        decoded_response = None
        # wait for auction information response
        while True:
            response, _ = unicast_listener.receive()

            decoded_response = msgs.decode(response)
            if decoded_response["tag"] != msgs.tag.AUCTION_INFORMATION_RESPONSE_TAG:
                continue

            decoded_response = msgs.AuctionInformationResponse.decode(response)
            if decoded_response._id != auction_id:
                continue
            break

        if decoded_response is None:
            self.logger.error(
                f"Could not get auction information for auction {auction_id}"
            )
            return

        auction: Auction = self.manager.Auction(
            decoded_response.item,
            decoded_response.price,
            decoded_response.time,
            decoded_response.auction_id,
            decoded_response.multicast_group,
            decoded_response.multicast_port,
        )
        auction.set_state(decoded_response.auction_state)
        auction.set_bid_history(decoded_response.bid_history)
        auction.set_winner(decoded_response.winner)

        # Join auction by joining multicast group of auction
        auction_listener: multiprocessing.Process = multiprocessing.Process(
            target=self._auction_listener, args=(auction,)
        )
        auction_listener.start()

        self._joined_auctions[auction_id] = auction
        self._auction_listeners[auction_id] = auction_listener

    def _leave_auction(self) -> None:
        """Leaves an auction"""
        auction_id = self._choose_auction(list(self._joined_auctions.keys()))
        if auction_id not in self._joined_auctions:
            self.logger.error(
                f"Auction with id {auction_id} not joined. This should not happen."
            )
            return
        self._joined_auctions.pop(auction_id)
        self._auction_listeners.pop(auction_id).terminate()

    def _bid(self) -> None:
        """Bids in an auction"""
        auction_id = self._choose_auction(list(self._joined_auctions.keys()))
        bid_amount = self._bid_amount()

        auction = self._joined_auctions[auction_id]
        if auction.get_state() != 1:
            self.logger.error(
                f"Auction with id {auction_id} is not running. Cannot bid."
            )
            return
        if bid_amount <= auction.get_highest_bid():
            self.logger.error(
                f"Bid amount {bid_amount} is not higher than highest bid {auction.get_highest_bid()}"
            )
            return

        auction.bid(self.name, bid_amount)

        mc_group, mc_port = auction.get_multicast_group_port()
        mc_sender = Multicast(
            mc_group,
            mc_port,
        )
        mc_sender.send(
            msgs.AuctionBid(
                _id=str(uuid.uuid4()),
                auction_id=auction_id,
                bidder=self.name,
                bid=bid_amount,
            ).encode()
        )

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

    def _bid_amount(self) -> float:
        """Prompts the user for a bid amount.

        Returns:
            float: The bid amount.
        """
        return float(
            inquirer.prompt(
                [
                    inquirer.Text(
                        "bid_amount",
                        message=inter.BIDDER_BID_AMOUNT_QUESTION,
                        validate=lambda _, x: re.match(r"^\d+(\.\d{1,2})?$", x)
                        is not None,
                    )
                ]
            )["bid_amount"]
        )
