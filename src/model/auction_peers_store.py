from ipaddress import IPv4Address
from typing import Iterator


class AuctionPeersStore:
    """The auction peers store class stores auction peers."""

    def __init__(self) -> None:
        self._peers: list[tuple[IPv4Address, int]] = []

    def add(self, address: IPv4Address, port: int) -> None:
        """Adds an Address to the store.

        Args:
            address (IPv4Address): The IPv4Address to add.
            port (int): The port of the Address to add.
        """
        if self.exists(address, port):
            raise ValueError(f"Address {address}:{port} already exists")
        self._peers.append((address, port))

    def remove(self, address: IPv4Address, port: int) -> None:
        """Removes an Address from the store.

        Args:
            address (IPv4Address): The IPv4Address to remove.
            port (int): The port of the Address to remove.

        Raises:
            ValueError: If the Address does not exist in the store.
        """
        if not self.exists(address, port):
            raise ValueError(f"Address {address}:{port} does not exist")
        self._peers.remove((address, port))

    def exists(self, address: IPv4Address, port: int) -> bool:
        """Returns whether an auction announcement exists in the store.

        Args:
            address (IPv4Address): The IPv4Address to check.
            port (int): The port of the Address to check.

        Returns:
            bool: Whether the IPv4Address exists in the store.
        """
        return (address, port) in self._peers

    def append(self, addresses: list[tuple[IPv4Address, int]]) -> None:
        """Adds a list of Addresses to the store.

        Args:
            addresses (list[tuple[IPv4Address, int]]): The list of Addresses to add.

        Raises:
            ValueError: If an Address already exists in the store.
        """
        for address in addresses:
            if address in self._peers:
                raise ValueError(f"{address} already exists")
            self.add(address[0], address[1])

    def replace(self, addresses: list[tuple[IPv4Address, int]]) -> bool:
        """Replaces the store with a new list of Addresses.

        Args:
            addresses (list[tuple[IPv4Address, int]]): The list of Addresses to replace the store with.

        Returns:
            bool: Whether changes were made to the store.
        """
        if set(addresses) == set(self._peers):
            return False
        self._peers = addresses
        return True

    def len(self) -> int:
        """Returns the length of the store, i.e. the number of peers.

        This method needs to be used, if the store is in shared memory (i.e. the store is a proxy object)

        Returns:
            int: The length of the store.
        """
        return len(self._peers)

    def iter(self) -> Iterator[tuple[IPv4Address, int]]:
        """Returns an iterator over the peers.

        This method needs to be used, if the store is in shared memory (i.e. the store is a proxy object)

        Returns:
            Iterator[tuple[IPv4Address, int]]: An iterator over the peers.
        """
        return iter(self._peers)

    def __len__(self) -> int:
        """Returns the length of the store, i.e. the number of peers.

        Returns:
            int: The length of the store.
        """
        return len(self._peers)

    def __iter__(self) -> Iterator[tuple[IPv4Address, int]]:
        """Returns an iterator over the peers.

        Returns:
            Iterator[tuple[IPv4Address, int]]: An iterator over the peers.
        """
        return iter(self._peers)
