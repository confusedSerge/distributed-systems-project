from __future__ import annotations

from ipaddress import IPv4Address


class Leader:
    """This is a wrapper class for shared memory leader object.

    This class is used to store the leader of the auction.
    """

    def __init__(self, address: IPv4Address, port: int) -> None:
        """Initializes the leader class.

        Args:
            address (IPv4Address): The address of the leader.
            port (int): The port of the leader.
        """
        self._address: IPv4Address = address
        self._port: int = port

    def get(self) -> tuple[IPv4Address, int]:
        """Returns the address and port of the leader.

        Returns:
            tuple[IPv4Address, int]: The address and port of the leader.
        """
        return self._address, self._port

    def set(self, address: IPv4Address, port: int) -> None:
        """Sets the address and port of the leader.

        Args:
            address (IPv4Address): The address of the leader.
            port (int): The port of the leader.
        """
        self._address = address
        self._port = port
