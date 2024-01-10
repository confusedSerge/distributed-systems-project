import socket
import struct

from typing import Optional


class Multicast:
    """Multicast class for sending and receiving multicast messages.

    This class implements a reliable, totally ordered multicast protocol.
    It is based on the ISIS algorithm.

    TODO: Implement the ISIS algorithm. Currently, this class has basic UDP Multicast functionality.
    """

    def __init__(
        self,
        group: str,
        port: int,
        sender: bool = False,
        ttl: int = 32,
        timeout: Optional[int] = None,
    ):
        """Initialize the multicast class.

        Args:
            group (str): The multicast group to send and receive messages.
            port (int): The port to send and receive messages.
            sender (bool, optional): Whether the multicast object is used for sending or receiving. Defaults to False.
            ttl (int, optional): The time to live for the multicast messages. Defaults to 32.
            timeout (Optional[int], optional): The timeout for receiving messages. Defaults to None, which does not trigger a timeout.
        """
        self._group: str = group
        self._port: int = port if isinstance(port, int) else int(port)
        self._multicast_group: tuple[str, int] = (self._group, self._port)

        self._sender: bool = sender
        self._socket: socket = None

        self._timeout: Optional[int] = timeout

        # Create the socket for multicast sender/receiver
        if sender:
            self._socket = socket.socket(
                socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP
            )
            self._socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)
        else:
            self._socket = socket.socket(
                socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP
            )
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            self._socket.setsockopt(
                socket.IPPROTO_IP,
                socket.IP_ADD_MEMBERSHIP,
                struct.pack("4sl", socket.inet_aton(self._group), socket.INADDR_ANY),
            )
            self._socket.settimeout(self._timeout) if self._timeout else None
            self._socket.bind(self._multicast_group)

    def send(self, message: bytes) -> None:
        """Send a message to the multicast group.

        Args:
            message (bytes): The message to send in bytes.
        """
        assert self._sender, "The multicast object is not a sender."
        self._socket.sendto(message, self._multicast_group)

    def receive(self, buffer_size: int = 1024) -> (bytes, str):
        """Receive a message from the multicast group.

        Args:
            buffer_size (int): The buffer size for the received message. Defaults to 1024.

        Returns:
            bytes: The received message.
            str: The address of the sender.

        Raises:
            socket.timeout: If the timeout is set and no message was received.
        """
        assert not self._sender, "The multicast object is not a receiver."
        return self._socket.recvfrom(buffer_size)

    def close(self) -> None:
        """Close the multicast socket."""
        self._socket.close()

    @staticmethod
    def qsend(message: bytes, group: str, port: int, ttl: int = 32) -> None:
        """Send a message to the multicast group.

        Args:
            message (bytes): The message to send in bytes.
            group (str): The multicast group to send and receive messages.
            port (int): The port to send and receive messages.
            ttl (int, optional): The time to live for the multicast messages. Defaults to 32.
        """
        mc = Multicast(group, port, sender=True, ttl=ttl)
        mc.send(message)
        mc.close()
