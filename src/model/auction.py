from constant import auction as auction_constant


class Auction:
    """Auction class handling the data of an auction.

    This includes the item, starting price, time, bid history and winner.
    """

    def __init__(
        self,
        item: str,
        price: float,
        time: int,
        _id: str,
        multicast_group: str = "",
        multicast_port: int = 0,
    ) -> None:
        """Initializes the auction class.

        Args:
            item (str): The item of the auction.
            price (float): The starting price of the auction.
            time (int): The time of the auction.
            _id (str): The id of the auction.
        """
        self._id: str = _id
        self._item: str = item
        self._price: float = price
        self._time: int = time

        # Multicast group and port are initially empty
        self._multicast_group: str = multicast_group
        self._multicast_port: int = multicast_port

        # Auction state is initially not started
        self._auction_state: tuple[int, str] = auction_constant.AUCTION_NOT_STARTED

        # Bid history is a list of tuples (bidder, bid)
        self._bid_history: list[tuple[str, float]] = []
        self._winner: str = ""

    def get_item(self) -> tuple[str, float, int]:
        """Returns the item, price and time of the auction.

        Returns:
            tuple[str, float, int]: _description_
        """
        return self._item, self._price, self._time

    def bid(self, bidder: str, bid: float) -> None:
        """Adds a bid to the bid history.

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

    def set_bid_history(self, bid_history: list[tuple[str, float]]) -> None:
        """Sets the bid history.

        Args:
            bid_history (list[tuple[str, float]]): The bid history.
        """
        self._bid_history = bid_history

    def get_highest_bid(self) -> tuple[str, float]:
        """Returns the highest bid.

        Returns:
            tuple[str, float]: The highest bid.
        """
        return max(self._bid_history, key=lambda x: x[1])

    def get_winner(self) -> str:
        """Returns the winner of the auction.

        Returns:
            str: The winner of the auction.
        """
        return self._winner

    def set_winner(self, winner: str) -> None:
        """Sets the winner of the auction.

        Args:
            winner (str): The winner of the auction.
        """
        self._winner = winner

    def get_id(self) -> str:
        """Returns the id of the auction.

        Returns:
            str: The id of the auction.
        """
        return self._id

    def get_multicast_group_port(self) -> tuple[str, int]:
        """Returns the multicast group and port of the auction.

        Returns:
            str: The multicast group and port of the auction.
        """
        return (self._multicast_group, self._multicast_port)

    def next_state(self) -> None:
        """Sets the next state of the auction."""
        match self._auction_state:
            case auction_constant.AUCTION_NOT_STARTED:
                self._auction_state = auction_constant.AUCTION_RUNNING
            case auction_constant.AUCTION_RUNNING:
                self._auction_state = auction_constant.AUCTION_ENDED
            case auction_constant.AUCTION_ENDED:
                self._auction_state = auction_constant.AUCTION_NOT_STARTED

    def get_state(self) -> tuple[int, str]:
        """Returns the state of the auction.

        Returns:
            tuple[int, str]: The state of the auction.
        """
        return self._auction_state

    def set_state(self, state: tuple[int, str]) -> None:
        """Sets the state of the auction.

        Args:
            state (tuple[int, str]): The state of the auction.
        """
        self._auction_state = state

    def __str__(self) -> str:
        return f"Auction {self._id} with ({self._item}, {self._price}, {self._time}) currently in state {self._auction_state[1]}"

    def __repr__(self) -> str:
        return str(self)
