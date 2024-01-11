from communication import MessageAuctionAnnouncement


class AuctionAnnouncementStore:
    """The auction announcement store class stores auction announcements.

    This is used by the bidder to keep track of auctions.
    """

    def __init__(self) -> None:
        self._auctions: dict[str, MessageAuctionAnnouncement] = {}

    def add(self, auction: MessageAuctionAnnouncement) -> None:
        """Adds an auction announcement to the store.

        Args:
            auction (MessageAuctionAnnouncement): The auction announcement to add.
        """
        if self.exists(auction._id):
            raise ValueError(f"Auction with id {auction._id} already exists")
        self._auctions[auction._id] = auction

    def get(self, auction: str) -> MessageAuctionAnnouncement:
        """Returns an auction announcement from the store.

        Args:
            auction_id (str): The auction id of the auction announcement to get.

        Returns:
            MessageAuctionAnnouncement: The auction announcement.
        """
        if not self.exists(auction):
            raise ValueError(f"Auction with id {auction} does not exist")
        return self._auctions[auction]

    def remove(self, auction: str) -> None:
        """Removes an auction announcement from the store.

        Args:
            auction_id (str): The auction id of the auction announcement to remove.
        """
        if not self.exists(auction):
            raise ValueError(f"Auction with id {auction} does not exist")
        del self._auctions[auction]

    def items(self) -> list[tuple[str, MessageAuctionAnnouncement]]:
        """Returns the items of the store.

        Returns:
            list[tuple[str, MessageAuctionAnnouncement]]: The items of the store.
        """
        return self._auctions.items()

    def exists(self, auction: str) -> bool:
        """Returns whether an auction announcement exists in the store.

        Args:
            auction_id (str): The auction id of the auction announcement to check.

        Returns:
            bool: Whether the auction announcement exists in the store.
        """
        return auction in self._auctions
