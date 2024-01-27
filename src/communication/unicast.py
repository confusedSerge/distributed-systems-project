from ipaddress import IPv4Address
import socket

from typing import Optional


class Unicast:
    """Unicast class for sending and receiving unicast messages."""

    def __init__(
        self,
        timeout: Optional[int] = None,
        no_bind: Optional[bool] = False,
    ):
        """Initialize the unicast socket.

        As we are using UDP, we can reuse the same address and port for sending and receiving messages.

        Args:
            host (IPv4Address): The host to send and receive messages. None will bind to all interfaces.
            port (int): The port to send and receive messages.
            timeout (int, optional): The timeout for receiving messages. Defaults to None.
            sender (bool, optional): Whether the unicast object is used for sending or receiving. Defaults to False.
        """
        self._socket: socket.socket = None
        self._no_bind: bool = no_bind

        # https://stackoverflow.com/questions/54192308/how-to-duplicate-udp-packets-to-two-or-more-sockets
        # https://stackoverflow.com/questions/21179042/linux-udp-socket-port-reuse
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        if not no_bind:
            self._socket.settimeout(timeout) if timeout else None
            self._socket.bind(("", 0))

    def send(self, message: bytes, address: tuple[IPv4Address, int] = None) -> None:
        """Send a message to the unicast host.

        Args:
            message (str): The message to send.
        """
        self._socket.sendto(message, (str(address[0]), address[1]))

    def receive(self, buffer_size: int = 1024) -> tuple[bytes, tuple[IPv4Address, int]]:
        """Receive a message from the unicast host.

        Args:
            buffer_size (int): The buffer size for the received message. Defaults to 1024.

        Returns:
            bytes: The received message.
            tuple[str, int]: The address of the sender.
        """
        assert not self._no_bind, "Cannot receive on unbound socket"
        message, address = self._socket.recvfrom(buffer_size)
        return message, (IPv4Address(address[0]), address[1])

    def close(self) -> None:
        """Close the unicast socket."""
        self._socket.close()

    def get_address(self) -> tuple[IPv4Address, int]:
        """Returns the address of the unicast socket.

        Returns:
            int: The address of the unicast socket.
        """
        return (IPv4Address(Unicast.get_host()), self._socket.getsockname()[1])

    @staticmethod
    def get_host() -> str:
        """Returns the host of the unicast socket.

        Returns:
            str: The host of the unicast socket.
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("10.0.0.3", 1234))
        return sock.getsockname()[0]

    @staticmethod
    def qsend(message: bytes, host: IPv4Address, port: int) -> None:
        """Send a message to the unicast host.

        Args:
            message (bytes): The message to send.
            host (IPv4Address): The host to send the message to.
            port (int): The port to send the message to.
        """
        uc = Unicast(no_bind=True)
        uc.send(message, (str(host), port))
        uc.close()
