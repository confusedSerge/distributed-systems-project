from typing import Optional

from ipaddress import IPv4Address
import socket

from hashlib import sha256

# === Custom Modules ===
from .messages import (
    MessageSchema,
    MessageReliableRequest,
    MessageReliableResponse,
)

from util import Timeout, generate_message_id

# === Constants ===
from constant import BUFFER_SIZE, HEADER_RELIABLE_REQ, HEADER_RELIABLE_RES


class Unicast:
    """Unicast class for sending and receiving unicast messages."""

    def __init__(
        self, timeout: Optional[int] = None, no_bind: bool = False, port: int = 0
    ):
        """Initialize the unicast socket.

        The unicast socket can be used to send messages to a specific host and port and receive messages from other hosts.
        Messages are sent and received using the UDP protocol.

        Args:
            timeout (int, optional): The timeout for receiving messages. Defaults to None.
            no_bind (bool, optional): Whether to bind the socket. Defaults to False.
            port (int, optional): The port to bind the socket to. Defaults to 0.
        """
        self._no_bind: bool = no_bind

        # https://stackoverflow.com/questions/54192308/how-to-duplicate-udp-packets-to-two-or-more-sockets
        # https://stackoverflow.com/questions/21179042/linux-udp-socket-port-reuse
        self._socket: socket.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        if not no_bind:
            self._socket.settimeout(timeout) if timeout else None
            self._socket.bind(("", port))

    def send(self, message: bytes, address: tuple[IPv4Address, int]) -> None:
        """Send a message to the unicast host.

        Args:
            message (str): The message to send.
        """
        self._socket.sendto(message, (str(address[0]), address[1]))

    def receive(
        self, buffer_size: int = BUFFER_SIZE
    ) -> tuple[bytes, tuple[IPv4Address, int]]:
        """Receive a message from the unicast host.

        Args:
            buffer_size (int): The buffer size for the received message. Defaults to BUFFER_SIZE.

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
        uc.send(message, (host, port))
        uc.close()


class ReliableUnicast:
    """ReliableUnicast class for sending and receiving reliable unicast messages."""

    def __init__(self, timeout: int = 1, retry: int = 5):
        """Initialize the reliable unicast socket.

        The reliable unicast socket can be used to send messages to a specific host and port and receive messages from other hosts.
        Messages are sent and received using the UDP protocol.
        This class sends and receives are upper bound by timeout times retries and will raise a TimeoutError if the message is not sent or received on time.

        Args:
            timeout (int, optional): The timeout for receiving messages. Defaults to 1.
            retry (int, optional): The number of times to retry sending a message. Defaults to 5.
        """
        self._timeout: int = timeout
        self._retry: int = retry
        self._unicast: Unicast = Unicast()

        # Duplicate protection
        self._acknowledged: set[str] = set()

    def send(self, message: bytes, address: tuple[IPv4Address, int]) -> None:
        """Send a message to the unicast host.

        The message is sent with a unique message id and a checksum to ensure the message is not duplicated and is not corrupted.
        The message is sent multiple times to ensure it is received.
        The upper bound for sending a message is timeout times retries.

        Args:
            message (str): The message to send.

        Raises:
            TimeoutError: If the message is not sent on time.
        """
        message_id: str = generate_message_id()
        wrapped_message: bytes = MessageReliableRequest(
            _id=message_id,
            checksum=sha256(message).hexdigest(),
            payload=message.decode(),
        ).encode()

        for _ in range(self._retry):
            try:
                self._unicast.send(wrapped_message, address)
                with Timeout(self._timeout):
                    message, from_address = self._unicast.receive()

                    if (
                        address == from_address
                        and MessageSchema.of(HEADER_RELIABLE_RES, message=message)
                        and MessageSchema.get_id(message=message) == message_id
                    ):
                        return
            except TimeoutError:
                pass

        raise TimeoutError

    def receive(self) -> tuple[bytes, tuple[IPv4Address, int]]:
        """Receive a message from the unicast host.

        If the message is not received on time, a TimeoutError will be raised.
        The upper bound for receiving a message is timeout times retries.

        Returns:
            bytes: The received message.
            tuple[str, int]: The address of the sender.

        Raises:
            TimeoutError: If no message is received on time.
        """
        try:
            with Timeout(self._timeout * self._retry):
                while True:
                    message, address = self._unicast.receive()

                    if not MessageSchema.of(HEADER_RELIABLE_REQ, message=message):
                        continue

                    reliable_req = MessageReliableRequest.decode(message)

                    if (
                        sha256(reliable_req.payload.encode()).hexdigest()
                        != reliable_req.checksum
                    ):
                        continue

                    response = MessageReliableResponse(
                        _id=reliable_req._id,
                    ).encode()
                    self._unicast.send(response, address)

                    if reliable_req._id in self._acknowledged:
                        continue

                    self._acknowledged.add(reliable_req._id)
                    return reliable_req.payload.encode(), address
        except TimeoutError:
            pass

        raise TimeoutError

    def close(self) -> None:
        """Close the unicast socket."""
        self._unicast.close()

    def get_address(self) -> tuple[IPv4Address, int]:
        """Returns the address of the unicast socket.

        Returns:
            int: The address of the unicast socket.
        """
        return self._unicast.get_address()

    @staticmethod
    def qsend(message: bytes, host: IPv4Address, port: int) -> None:
        """For reliable unicast, quick send is not supported."""
        raise NotImplementedError
