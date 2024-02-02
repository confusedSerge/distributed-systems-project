from multiprocessing.synchronize import Event

from logging import Logger
from time import localtime, strftime
from typing import Optional

import re
import inquirer

# === Custom Modules ===

from model import Auction, AuctionAnnouncementStore
from process import Manager, AuctionBidListener
from communication import (
    Multicast,
    Unicast,
    MessageSchema,
    AuctionMessageData,
    MessageAuctionInformationRequest,
    MessageAuctionInformationResponse,
    MessageAuctionBid,
)

from util import create_logger, Timeout, generate_message_id

from constant import (
    interaction as inter,
    communication as com,
    stateid2stateobj,
    USERNAME,
    BUFFER_SIZE,
    TIMEOUT_RESPONSE,
    MULTICAST_DISCOVERY_GROUP,
    MULTICAST_DISCOVERY_PORT,
    MULTICAST_DISCOVERY_TTL,
    MULTICAST_AUCTION_PORT,
)


class Bidder:
    """The bidder class handles the bidding process of the client.

    Bidder is run in the client thread and delegates its background tasks (listeners) to other processes, sharing the same memory.

    The bidder class provides an interactive command line interface to the user to join auctions, place bids and leave auctions.
    The bidder class also handles the auction information requests and responses.
    """

    def __init__(
        self,
        manager: Manager,
        manager_running: Event,
        auction_announcement_store: AuctionAnnouncementStore,
    ) -> None:
        """Initializes the bidder class.

        The auction announcement store is used to keep track of current auctions.
        This allows to choose unique auction ids and multicast groups for each auction.

        Args:
            manager (Manager): The manager to use for shared memory.
            manager_running (Event): The event to use to check if the manager is running.
            auction_announcement_store (AuctionAnnouncementStore): The auction announcement store to store the auction announcements in. Should be a shared memory object.
        """
        self._name: str = "Bidder"
        self._logger: Logger = create_logger(self._name.lower())

        # Shared memory
        self.manager: Manager = manager
        self.manager_running: Event = manager_running
        self.auction_announcement_store: AuctionAnnouncementStore = (
            auction_announcement_store
        )

        # Keep track of joined auctions and their listeners
        self._joined_auctions: dict[str, Auction] = {}
        self._auction_bid_listeners: dict[str, AuctionBidListener] = {}

        self._logger.info(f"{self._name}: Initialized")

    def stop(self) -> None:
        """Stops the bidder background tasks."""
        self._logger.info(f"{self._name}: Releasing resources")

        for auction_listener in self._auction_bid_listeners.values():
            auction_listener.stop()

        for auction_listener in self._auction_bid_listeners.values():
            auction_listener.join()

        self._logger.info(f"{self._name}: Stopped")

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

            if answer is None:
                break

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
                    self._logger.error(
                        f"{self._name}: Invalid action {answer['action']}"
                    )

    # === Interaction Methods ===

    def _list_auctions(self) -> None:
        """Lists the auctions available to join."""
        print("Auctions available to join:")
        for _, auction in self.auction_announcement_store.items():
            print(
                f"Auction {auction.auction._id} with ({auction.auction.item}, {auction.auction.price}, {strftime('%a, %d %b %Y %H:%M:%S +0000', localtime(auction.auction.time))}) currently in state {stateid2stateobj[auction.auction.state][1]}"
            )

    def _list_auction_info(self) -> None:
        """Lists the information of an auction."""
        auction_id: str | None = self._choose_auction(
            list(self._joined_auctions.keys())
        )
        if auction_id is None:
            return
        auction = self._joined_auctions[auction_id]
        print(f"Information about auction {auction_id}:")
        print(f"* Joined auction {auction_id}: {auction}")
        print(f"* Highest bid: {auction.get_highest_bid()}")
        print(
            f"* Winner: {auction.get_winner() if auction.is_ended() else 'No winner yet'}"
        )

    def _join_auction(self) -> None:
        """Joins an auction"""
        # Choose auction to join from auctions that have not been joined yet
        not_joined_auctions: list[str] = [
            auction.auction._id
            for _, auction in self.auction_announcement_store.items()
            if auction.auction._id not in self._joined_auctions
        ]
        auction: str | None = self._choose_auction(not_joined_auctions)
        if auction is None:
            return

        # Query auction information
        response: Optional[Auction] = self._fetch_auction_information(auction)
        if response is None:
            print(f"Could not get auction information for auction {auction}")
            return

        listener: AuctionBidListener = AuctionBidListener(response)
        listener.start()

        self._joined_auctions[auction] = response
        self._auction_bid_listeners[auction] = listener

    def _leave_auction(self) -> None:
        """Leaves an auction"""
        auction_id: str | None = self._choose_auction(
            list(self._joined_auctions.keys())
        )
        if auction_id is None:
            return

        self._joined_auctions.pop(auction_id)
        self._auction_bid_listeners.pop(auction_id).stop()

    def _bid(self) -> None:
        """Bids in an auction"""
        # Prompt for auction and bid amount
        auction_id: str | None = self._choose_auction(
            list(self._joined_auctions.keys())
        )
        if auction_id is None:
            return

        bid_amount: float | None = self._bid_amount()
        if bid_amount is None:
            return

        # Check if bid amount is higher than current highest bid
        auction: Auction = self._joined_auctions[auction_id]
        if not auction.is_running():
            print(f"Auction with id {auction} is not running. Cannot place bid.")
            return
        if bid_amount <= auction.get_highest_bid()[1]:
            print(
                f"Bid amount {bid_amount} is not higher than current highest bid {auction.get_highest_bid()}"
            )
            return

        # Place bid
        bid: MessageAuctionBid = MessageAuctionBid(
            _id=generate_message_id(auction.get_id()),
            bidder=USERNAME,
            bid=bid_amount,
        )
        Multicast.qsend(
            message=bid.encode(),
            group=auction.get_group(),
            port=MULTICAST_AUCTION_PORT,
        )
        self._logger.info(
            f"{self._name}: Sent bid {bid} for auction {auction.get_id()}"
        )

    # === Prompt Methods ===

    def _choose_auction(self, auctions: list[str]) -> None | str:
        """Chooses an auction.

        Prompts the user to choose an auction and returns the auction id.

        Args:
            auction (list[str]): The auction ids of the auctions to choose from.

        Returns:
            str: The auction id of the auction.
        """
        if len(auctions) == 0:
            print("No auctions available")
            return None

        answer = inquirer.prompt(
            [
                inquirer.List(
                    "auction",
                    message=inter.BIDDER_AUCTION_QUESTION,
                    choices=auctions,
                )
            ]
        )

        if answer is None:
            return None

        return str(answer["auction"])

    def _bid_amount(self) -> float | None:
        """Prompts the user for a bid amount.

        Returns:
            float: The bid amount.
        """
        answer = inquirer.prompt(
            [
                inquirer.Text(
                    "bid",
                    message=inter.BIDDER_BID_AMOUNT_QUESTION,
                    validate=lambda _, x: re.match(r"^\d+(\.\d{1,2})?$", x) is not None,
                )
            ]
        )

        if answer is None:
            return None

        return float(answer["bid"])

    # === Helper Methods ===

    def _get_auction_from_message(
        self, message: MessageAuctionInformationResponse
    ) -> Auction:
        """Handles an auction information message.

        Args:
            message (MessageAuctionInformationResponse): The auction information message.

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

    def _fetch_auction_information(self, auction: str) -> Optional[Auction]:
        """Gets the auction information for an auction.

        Args:
            auction (str): The auction to get the information for.

        Returns:
            Auction: The auction information. None if the auction information could not be retrieved.
        """
        # Prepare unicast socket
        uc: Unicast = Unicast()
        request_message_id: str = generate_message_id(auction)

        self._logger.info(
            f"{self._name}: Getting auction information for auction {auction}"
        )
        Multicast.qsend(
            message=MessageAuctionInformationRequest(
                _id=request_message_id, auction=auction, port=uc.get_address()[1]
            ).encode(),
            group=MULTICAST_DISCOVERY_GROUP,
            port=MULTICAST_DISCOVERY_PORT,
            ttl=MULTICAST_DISCOVERY_TTL,
        )
        self._logger.info(
            f"{self._name}: Sent auction information request for auction {auction}"
        )

        # wait for auction information response
        self._logger.info(
            f"{self._name}: Waiting for auction information response for auction {auction}"
        )
        try:
            with Timeout(TIMEOUT_RESPONSE, throw_exception=True):
                while True:
                    message, _ = uc.receive(BUFFER_SIZE)

                    if (
                        not MessageSchema.of(
                            com.HEADER_AUCTION_INFORMATION_RES, message
                        )
                        or MessageSchema.get_id(message) != request_message_id
                    ):
                        continue

                    response: MessageAuctionInformationResponse = (
                        MessageAuctionInformationResponse.decode(message)
                    )
                    break
        except TimeoutError:
            self._logger.info(
                f"{self._name}: Timed out waiting for auction information response for auction {auction}"
            )
            return None
        finally:
            uc.close()

        self._logger.info(
            f"{self._name}: Received auction information response for auction {auction}: {response}"
        )
        return self._get_auction_from_message(response)
