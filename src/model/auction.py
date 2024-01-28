from __future__ import annotations

from ipaddress import IPv4Address

from constant import auction as state


class Auction:
    """Auction class handling the data of an auction.

    This includes the item, starting price, time, bid history and winner.
    """

    def __init__(
        self,
        name: str,
        auctioneer: str,
        item: str,
        price: float,
        time: int,
        address: IPv4Address,
    ) -> None:
        """Initializes the auction class.

        Args:
            name (str): The name of the auction. Referred as uname.
            auctioneer (str): The auctioneer of the auction. Referred as aname.

            item (str): The item of the auction.
            price (float): The starting price of the auction.
            time (int): The time of the auction.

            multicast_address (IPv4Address): The multicast address of the auction. (port are constant for all auctions)
        """
        # Identification
        self._name: str = name
        self._auctioneer: str = auctioneer
        self._id: str = Auction.id(auctioneer, name)

        # Auction information
        self._item: str = item
        self._price: float = price
        self._time: int = time

        # Multicast group and port are initially empty
        self._multicast_group: IPv4Address = address

        # Auction states
        self._auction_state: tuple[int, str] = state.AUCTION_PREPARATION
        self._bid_history: list[tuple[str, float]] = []
        self._winner: str = ""

    # Identification methods
    def get_name(self) -> str:
        """Returns the name of the auction.

        Returns:
            str: The name of the auction.
        """
        return self._name

    def get_auctioneer(self) -> str:
        """Returns the auctioneer of the auction.

        Returns:
            str: The auctioneer of the auction.
        """
        return self._auctioneer

    def get_id(self) -> str:
        """Returns the id of the auction.

        Returns:
            str: The id of the auction (structure is "uname::aname").
        """
        return self._id

    def _set_id(self, id: str) -> None:
        """Sets the id of the auction.

        Should only be used when deserializing an auction.

        Args:
            id (str): The id of the auction.
        """
        self._id = id

    # Auction information methods
    def get_item(self) -> str:
        """Returns the item

        Returns:
            str: The item of the auction.
        """
        return self._item

    def get_price(self) -> float:
        """Returns the starting price of the auction.

        Returns:
            float: The price of the auction.
        """
        return self._price

    def get_time(self) -> int:
        """Returns the time of the auction.

        Returns:
            int: The time of the auction.
        """
        return self._time

    # Multicast methods
    def get_group(self) -> IPv4Address:
        """Returns the multicast group of the auction.

        Returns:
            IPv4Address: The multicast group of the auction.
        """
        return self._multicast_group

    # Auction state methods
    def get_state(self) -> tuple[int, str]:
        """Returns the state of the auction.

        Returns:
            tuple[int, str]: The state of the auction.
        """
        return self._auction_state

    def get_state_id(self) -> int:
        """Returns the state id of the auction.

        Returns:
            int: The state id of the auction.
        """
        return self._auction_state[0]

    def get_state_description(self) -> str:
        """Returns the state description of the auction.

        Returns:
            str: The state description of the auction.
        """
        return self._auction_state[1]

    def next_state(self) -> None:
        """Sets the state of the auction to the next state."""
        match self._auction_state:
            case state.AUCTION_PREPARATION:
                self._auction_state = state.AUCTION_RUNNING
            case state.AUCTION_RUNNING:
                self._auction_state = state.AUCTION_ENDED
            case state.AUCTION_ENDED:
                self._auction_state = state.AUCTION_WINNER_DECLARED
            case _:
                self._auction_state = state.AUCTION_CANCELLED

    def cancel(self) -> None:
        """Cancels the auction."""
        self._auction_state = state.AUCTION_CANCELLED

    def is_cancelled(self) -> bool:
        """Returns whether the auction is cancelled.

        Returns:
            bool: Whether the auction is cancelled.
        """
        return self._auction_state == state.AUCTION_CANCELLED

    def is_preparation(self) -> bool:
        """Returns whether the auction is in preparation.

        Returns:
            bool: Whether the auction is in preparation.
        """
        return self._auction_state == state.AUCTION_PREPARATION

    def is_running(self) -> bool:
        """Returns whether the auction is running.

        Returns:
            bool: Whether the auction is running.
        """
        return self._auction_state == state.AUCTION_RUNNING

    def is_ended(self) -> bool:
        """Returns whether the auction is ended.

        Returns:
            bool: Whether the auction is ended.
        """
        return self._auction_state == state.AUCTION_ENDED

    def is_winner_declared(self) -> bool:
        """Returns whether the auction winner has been declared.

        Returns:
            bool: Whether the auction winner has been declared.
        """
        return self._auction_state == state.AUCTION_WINNER_DECLARED

    def _set_state(self, state_id: int) -> None:
        """Sets the state of the auction.

        This method should only be used when deserializing an auction.

        Args:
            state_id (int): The state id of the auction.
        """
        self._auction_state = (
            state.stateid2stateobj[state_id]
            if state_id in state.stateid2stateobj
            else state.AUCTION_CANCELLED
        )

    def bid(self, bidder: str, bid: float) -> None:
        """Bids on the auction.

        Args:
            bidder (str): The bidder.
            bid (float): The bid.
        """
        self._bid_history.append((bidder, bid))

    def get_bid_history(self) -> list[tuple[str, float]]:
        """Returns the bid history.

        Returns:
            list[tuple[str, float]]: The bid history.
        """
        return self._bid_history

    def _set_bid_history(self, bid_history: list[tuple[str, float]]) -> None:
        """Sets the bid history.

        This method should only be used when deserializing an auction.

        Args:
            bid_history (list[tuple[str, float]]): The bid history.
        """
        self._bid_history = bid_history

    def get_highest_bid(self) -> tuple[str, float]:
        """Returns the highest bid.

        Returns:
            tuple[str, float]: The highest bid.
        """
        if len(self._bid_history) == 0:
            return ("n/a", 0.0)
        return max(self._bid_history, key=lambda x: x[1])

    def get_winner(self) -> str:
        """Returns the winner of the auction.

        Returns:
            str: The winner of the auction.
        """
        if self._auction_state == state.AUCTION_WINNER_DECLARED:
            return self._winner
        return ""

    def _set_winner(self, winner: str) -> None:
        """Sets the winner of the auction.

        This method should only be used when deserializing an auction.

        Args:
            winner (str): The winner of the auction.
        """
        self._winner = winner

    def __str__(self) -> str:
        return f"Auction {self._id} with ({self._item}, {self._price}, {self._time}) currently in state {self._auction_state[1]}"

    def __repr__(self) -> str:
        return str(self)

    def from_other(self, other: Auction) -> None:
        """Replace the auction with another auction.

        Args:
            other (Auction): The other auction.
        """
        self._name = other.get_name()
        self._auctioneer = other.get_auctioneer()
        self._id = other.get_id()

        self._item = other.get_item()
        self._price = other.get_price()
        self._time = other.get_time()

        self._multicast_group = other.get_group()

        self._auction_state = other.get_state()
        self._bid_history = other.get_bid_history()
        self._winner = other.get_winner()

    @staticmethod
    def copy(other: Auction) -> Auction:
        """Returns a copy of the auction.

        Args:
            other (Auction): The auction to copy.

        Returns:
            Auction: The copy of the auction.
        """
        auction: Auction = Auction(
            name=other.get_name(),
            auctioneer=other.get_auctioneer(),
            item=other.get_item(),
            price=other.get_price(),
            time=other.get_time(),
            address=other.get_group(),
        )
        auction._set_id(other.get_id())
        auction._set_state(other.get_state_id())
        auction._set_bid_history(other.get_bid_history())
        auction._set_winner(other.get_winner())
        return auction

    @staticmethod
    def id(auctioneer: str, name: str) -> str:
        """Returns the id of the auction.

        Args:
            name (str): The name of the auction.
            auctioneer (str): The auctioneer of the auction.

        Returns:
            str: The id of the auction.
        """
        return f"{auctioneer}::{name}".lower()

    @staticmethod
    def parse_id(_id: str) -> str:
        """Parses from the input id the auction id.

        The id is assumed to be in the format "uname::aname(::uuid)".

        Args:
            id (str): The id to parse.

        Returns:
            str: The auction id.

        Raises:
            ValueError: If the id is not in the correct format.
        """
        split: list[str] = _id.split("::")
        if len(split) == 2 or len(split) == 3:
            return Auction.id(split[0], split[1])
        raise ValueError("Invalid id given for parsing: {id}")
