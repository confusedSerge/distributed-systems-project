import socket
import struct
import os


class Multicast:
    """Multicast class for sending and receiving multicast messages.

    This class implements a reliable, totally ordered multicast protocol.
    It is based on the ISIS algorithm.

    TODO: Implement the ISIS algorithm. Currently, this class has basic UDP Multicast functionality.
    """

    def __init__(self, group: str, port: int, ttl: int = 1) -> None:
        """Initialize the multicast class.

        Args:
            group (str): The multicast group to send and receive messages.
            port (int): The port to send and receive messages.
            ttl (int, optional): The time to live for the multicast messages. Defaults to 1.
        """
        self.group = group
        self.port = port if isinstance(port, int) else int(port)
        self.multicast_group = (self.group, self.port)

        # Create the socket for multicast receiver
        self.multicast_receiver = socket.socket(
            socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP
        )
        if os.name == "nt":
            self.multicast_receiver.bind(("", self.port))
        else:
            self.multicast_receiver.bind(self.multicast_group)

        self.multicast_receiver.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.multicast_receiver.setsockopt(
            socket.IPPROTO_IP,
            socket.IP_ADD_MEMBERSHIP,
            struct.pack("4sl", socket.inet_aton(self.group), socket.INADDR_ANY),
        )

        # Create the socket for multicast sender
        self.multicast_sender = socket.socket(
            socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP
        )
        self.multicast_sender.setsockopt(
            socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl
        )

    def send(self, message: str) -> None:
        """Send a message to the multicast group.

        Args:
            message (str): The message to send.
        """
        self.multicast_sender.sendto(message.encode(), self.multicast_group)

    def receive(self, buffer_size: int = 1024) -> str:
        """Receive a message from the multicast group.

        Args:
            buffer_size (int): The buffer size for the received message. Defaults to 1024.

        Returns:
            str: The received message.
        """
        return self.multicast_receiver.recv(buffer_size).decode()
