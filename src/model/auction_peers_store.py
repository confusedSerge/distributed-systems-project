from ipaddress import IPv4Address
from typing import Iterator


class AuctionPeersStore:
    """The auction peers store class stores auction peers as IPv4Address objects."""

    def __init__(self) -> None:
        self._peers: list[IPv4Address] = []

    def add(self, address: IPv4Address) -> None:
        """Adds an IPv4Address to the store.

        Args:
            address (IPv4Address): The IPv4Address to add.
        """
        if self.exists(address):
            raise ValueError(f"Address {address} already exists")
        self._peers.append(address)

    def remove(self, address: int) -> None:
        """Removes an auction announcement from the store.

        Args:
            address (int): The auction id of the auction announcement to remove.
        """
        if not self.exists(address):
            raise ValueError(f"Auction with id {address} does not exist")
        del self._peers[address]

    def exists(self, address: IPv4Address) -> bool:
        """Returns whether an auction announcement exists in the store.

        Args:
            address (IPv4Address): The IPv4Address to check.

        Returns:
            bool: Whether the IPv4Address exists in the store.
        """
        return address in self._peers

    def append(self, addresses: list[IPv4Address]) -> None:
        """Adds a list of IPv4Addresses to the store.

        Args:
            addresses (list[IPv4Address]): The list of IPv4Addresses to add.

        Raises:
            ValueError: If an IPv4Address already exists in the store.
        """
        for address in addresses:
            if address in self._peers:
                raise ValueError(f"Address {address} already exists")
            self.add(address)

    def replace(self, addresses: list[IPv4Address]) -> None:
        """Replaces the store with a new list of IPv4Addresses.

        Args:
            addresses (list[IPv4Address]): The list of IPv4Addresses to replace the store with.
        """
        self._peers = addresses

    def len(self) -> int:
        """Returns the length of the store, i.e. the number of peers.

        This method needs to be used, if the store is in shared memory (i.e. the store is a proxy object)

        Returns:
            int: The length of the store.
        """
        return len(self._peers)

    def __iter__(self) -> Iterator[IPv4Address]:
        """Returns an iterator over the peers.

        Returns:
            Iterator[IPv4Address]: An iterator over the peers.
        """
        return iter(self._peers)

    def __len__(self) -> int:
        """Returns the length of the store, i.e. the number of peers.

        Returns:
            int: The length of the store.
        """
        return len(self._peers)
