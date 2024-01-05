from constant import auction as auction_constant


class Auction:
    """Auction class handling the data of an auction.

    This includes the item, starting price, time, bid history and winner.
    """

    def __init__(self, item: str, price: float, time: int) -> None:
        self._item: str = item
        self._price: float = price
        self._time: int = time

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

    def __str__(self) -> str:
        return f"Auction for {self._item} with starting price {self._price} and time {self._time} currently in state {self._auction_state[1]}"
