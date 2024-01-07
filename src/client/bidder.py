import uuid
from multiprocessing import Process, Event

import inquirer

from model import Auction, AuctionAnnouncementStore
from process import Manager, AuctionAnnouncementListener, AuctionBidListener
from communication import (
    Multicast,
    Unicast,
    MessageSchema,
    AuctionMessageData,
    MessageAuctionInformationRequest,
    MessageAuctionInformationResponse,
    MessageAuctionBid,
)


from util import create_logger, logging

from constant import (
    interaction as inter,
    header as hdr,
    MULTICAST_DISCOVERY_GROUP,
    MULTICAST_DISCOVERY_PORT,
    MULTICAST_DISCOVERY_TTL,
    UNICAST_PORT,
)


class Bidder(Process):
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

    def __init__(
        self,
    ) -> None:
        """Initializes the bidder class

        Args:
            config (dict): The configuration of the bidder.
        """
        super().__init__()
        self._exit = Event()

        self.name = "Bidder"
        self.logger: logging.Logger = create_logger(self.name.lower())

        # Shared memory
        self.manager_running = Event()
        self.manager: Manager = Manager()

        self._auction_announcement_store: AuctionAnnouncementStore = None
        self._auction_announcement_process: AuctionAnnouncementListener = None

        self._joined_auctions: dict[str, Auction] = {}
        self._auction_bid_listeners: dict[str, AuctionBidListener] = {}

    def start(self) -> None:
        """Starts the bidder background tasks."""
        self.logger.info(f"{self.name} is starting background tasks")

        self.manager.start()
        self.manager_running.set()

        # Start auction announcement listener
        self._auction_announcement_store = self.manager.AuctionAnnouncementStore()
        self._auction_announcement_process = AuctionAnnouncementListener(
            self._auction_announcement_store
        )
        self._auction_announcement_process.start()

        self.logger.info(f"{self.name} started background tasks")

    def stop(self) -> None:
        """Stops the bidder background tasks."""
        self.logger.info(f"{self.name} is stopping background tasks")

        self._auction_announcement_process.stop()

        for auction_listener in self._auction_bid_listeners.values():
            auction_listener.stop()

        self.manager_running.clear()
        self.manager.stop()

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
        """Joins an auction"""
        not_joined_auctions: list[str] = [
            auction_id
            for auction_id in self._auction_announcement_store.keys()
            if auction_id not in self._joined_auctions
        ]
        auction_id = self._choose_auction(not_joined_auctions)
        response: AuctionMessageData = self._get_auction_information(auction_id)

        if response is None:
            self.logger.error(
                f"Could not get auction information for auction {auction_id}"
            )
            return

        auction: Auction = AuctionMessageData.to_auction(response)
        listener: AuctionBidListener = AuctionBidListener(auction)
        listener.start()

        self._joined_auctions[auction_id] = auction
        self._auction_bid_listeners[auction_id] = listener

    def _get_auction_information(self, auction_id: str) -> AuctionMessageData:
        """Gets the auction information for an auction.

        Args:
            auction_id (str): The auction id of the auction to get the information for.

        Returns:
            AuctionMessageData: The auction information or None if the auction could not be found.
        """

        # Send auction information request
        uc = Unicast("", UNICAST_PORT, sender=False)
        Multicast.qsend(
            MessageAuctionInformationRequest(auction_id=auction_id).encode(),
            MULTICAST_DISCOVERY_GROUP,
            MULTICAST_DISCOVERY_PORT,
            MULTICAST_DISCOVERY_TTL,
        )

        # wait for auction information response
        # TODO: Timeout and return None
        while True:
            response, _ = uc.receive()

            if not MessageSchema.of(hdr.AUCTION_INFORMATION_RES, response):
                continue

            response: MessageAuctionInformationResponse = (
                MessageAuctionInformationResponse.decode(response)
            )
            if response._id != auction_id:
                continue

            break

        return response.auction_information

    def _leave_auction(self) -> None:
        """Leaves an auction"""
        auction_id = self._choose_auction(list(self._joined_auctions.keys()))
        if auction_id not in self._joined_auctions:
            self.logger.error(
                f"Auction with id {auction_id} not joined. This should not happen."
            )
            return
        self._joined_auctions.pop(auction_id)
        self._auction_bid_listeners.pop(auction_id).stop()

    def _bid(self) -> None:
        """Bids in an auction"""
        auction_id = self._choose_auction(list(self._joined_auctions.keys()))
        bid_amount = self._bid_amount()

        auction = self._joined_auctions[auction_id]
        if auction.get_state() != 1:
            print(f"Auction with id {auction_id} is not running. Cannot bid.")
            return
        if bid_amount <= auction.get_highest_bid():
            print(
                f"Bid amount {bid_amount} is not higher than highest bid {auction.get_highest_bid()}"
            )
            return

        auction.bid(self.name, bid_amount)
        Multicast.qsend(
            MessageAuctionBid(
                auction_id=auction_id,
                bidder_id=self.name,
                bid=bid_amount,
            ).encode(),
            group=auction.get_multicast_group(),
            port=auction.get_multicast_port(),
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
