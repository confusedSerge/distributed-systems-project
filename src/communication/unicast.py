from ipaddress import IPv4Address
import socket

from typing import Optional


class Unicast:
    """Unicast class for sending and receiving unicast messages."""

    def __init__(
        self,
        host: Optional[IPv4Address],
        port: int,
        sender: bool = False,
        timeout: Optional[int] = None,
    ):
        """Initialize the unicast socket.

        As we are using UDP, we can reuse the same address and port for sending and receiving messages.

        Args:
            host (IPv4Address): The host to send and receive messages.
            port (int): The port to send and receive messages.
            sender (bool, optional): Whether the unicast object is used for sending or receiving. Defaults to False.
        """
        assert (
            sender and not host or not sender and host
        ), "The host must be set, if and only if the unicast object is a sender."
        self._host: Optional[IPv4Address] = host
        self._port: int = port if isinstance(port, int) else int(port)
        self._address_port: tuple[str, int] = (
            "" if not host else str(host),
            self._port,
        )

        self._sender: bool = sender
        self._socket: socket = None

        if sender:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        else:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            self._socket.settimeout(timeout) if timeout else None
            self._socket.bind(self._address_port)

    def send(self, message: str) -> None:
        """Send a message to the unicast host.

        Args:
            message (str): The message to send.
        """
        assert self._sender, "The unicast object is not a sender."
        self._socket.sendto(message.encode(), self._address_port)

    def receive(self, buffer_size: int = 1024) -> (bytes, tuple[str, int]):
        """Receive a message from the unicast host.

        Args:
            buffer_size (int): The buffer size for the received message. Defaults to 1024.

        Returns:
            bytes: The received message.
            tuple[str, int]: The address of the sender.
        """
        assert not self._sender, "The unicast object is not a receiver."
        return self._socket.recvfrom(buffer_size)

    def close(self) -> None:
        """Close the unicast socket."""
        self._socket.close()

    @staticmethod
    def qsend(message: str, host: IPv4Address, port: int) -> None:
        """Send a message to the unicast host.

        Args:
            host (IPv4Address): The host to send the message to.
            port (int): The port to send the message to.
            message (str): The message to send.
        """
        uc = Unicast(host, port, sender=True)
        uc.send(message)
        uc.close()
