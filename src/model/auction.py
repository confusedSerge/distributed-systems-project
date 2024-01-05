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
        _id: int = 0,
        multicast_group: str = "",
        multicast_port: int = 0,
    ) -> None:
        """Initializes the auction class.

        Args:
            item (str): The item of the auction.
            price (float): The starting price of the auction.
            time (int): The time of the auction.
            _id (int, optional): The id of the auction. Defaults to 0.
        """
        self._id: int = _id
        self._item: str = item
        self._price: float = price
        self._time: int = time

        # Multicast group and port are initially empty
        self._multicast_group: str = ""
        self._multicast_port: int = 0

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

    def get_id(self) -> int:
        """Returns the id of the auction.

        Returns:
            int: The id of the auction.
        """
        return self._id

    def get_multicast_group_port(self) -> tuple[str, int]:
        """Returns the multicast group and port of the auction.

        Returns:
            str: The multicast group and port of the auction.
        """
        return (self._multicast_group, self._multicast_port)

    def __str__(self) -> str:
        return f"Auction for {self._item} with starting price {self._price} and time {self._time} currently in state {self._auction_state[1]}"
