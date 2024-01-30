from ipaddress import IPv4Address

from communication import MessageAuctionAnnouncement
from model import Auction


class AuctionAnnouncementStore:
    """The auction announcement store class stores auction announcements.

    This is used by the bidder to keep track of auctions.
    """

    def __init__(self) -> None:
        self._announcements: dict[str, MessageAuctionAnnouncement] = {}

    def add(self, announcement: MessageAuctionAnnouncement) -> None:
        """Adds an auction announcement to the store.

        Args:
            auction (MessageAuctionAnnouncement): The auction announcement to add.
        """
        if self.exists(Auction.parse_id(announcement._id)):
            raise ValueError(
                f"Auction with id {Auction.parse_id(announcement._id)} already exists"
            )

        self._announcements[Auction.parse_id(announcement._id)] = announcement

    def update(self, announcement: MessageAuctionAnnouncement) -> None:
        """Updates an auction announcement in the store.

        Currently, this just replaces the old auction announcement with the new one, if it exists.

        Args:
            auction (MessageAuctionAnnouncement): The auction announcement to update.
        """
        self._announcements[Auction.parse_id(announcement._id)] = announcement

    def get(self, auction: str) -> MessageAuctionAnnouncement:
        """Returns an auction announcement from the store.

        Args:
            auction_id (str): The auction id of the auction announcement to get.

        Returns:
            MessageAuctionAnnouncement: The auction announcement.
        """
        if not self.exists(auction):
            raise ValueError(f"Auction with id {auction} does not exist")
        return self._announcements[auction]

    def remove(self, auction: str) -> None:
        """Removes an auction announcement from the store.

        Args:
            auction_id (str): The auction id of the auction announcement to remove.
        """
        if not self.exists(auction):
            raise ValueError(f"Auction with id {auction} does not exist")
        del self._announcements[auction]

    def items(self) -> list[tuple[str, MessageAuctionAnnouncement]]:
        """Returns the items of the store.

        Returns:
            list[tuple[str, MessageAuctionAnnouncement]]: The items of the store.
        """
        return list(self._announcements.items())

    def exists(self, auction: str) -> bool:
        """Returns whether an auction announcement exists in the store.

        Args:
            auction_id (str): The auction id of the auction announcement to check.

        Returns:
            bool: Whether the auction announcement exists in the store.
        """
        return auction in self._announcements

    def keys(self) -> list[str]:
        """Returns the keys of the store.

        Returns:
            list[str]: The keys of the store.
        """
        return list(self._announcements.keys())

    def values(self) -> list[MessageAuctionAnnouncement]:
        """Returns the values of the store.

        Returns:
            list[MessageAuctionAnnouncement]: The values of the store.
        """
        return list(self._announcements.values())

    def get_groups(self) -> list[IPv4Address]:
        """Returns the address groups of the auctions in the store.

        Returns:
            list[IPv4Address]: The address groups of the auctions in the store.
        """
        return [
            IPv4Address(announcement.auction.group)
            for announcement in self._announcements.values()
        ]
