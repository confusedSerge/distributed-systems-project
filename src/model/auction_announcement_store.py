from communication import MessageAuctionAnnouncement


class AuctionAnnouncementStore:
    """The auction announcement store class stores auction announcements.

    This is used by the bidder to keep track of auctions.
    """

    def __init__(self) -> None:
        self._auctions: dict[int, MessageAuctionAnnouncement] = {}

    def add(self, auction: MessageAuctionAnnouncement) -> None:
        """Adds an auction announcement to the store.

        Args:
            auction (AuctionAnnouncement): The auction announcement to add.
        """
        if self.exists(auction._id):
            raise ValueError(f"Auction with id {auction._id} already exists")
        self._auctions[auction._id] = auction

    def get(self, auction_id: int) -> MessageAuctionAnnouncement:
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

    def items(self) -> list[tuple[int, MessageAuctionAnnouncement]]:
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
