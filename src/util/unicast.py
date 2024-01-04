import socket


class Unicast:
    """Unicast class for sending and receiving unicast messages."""

    def __init__(self, host: str, port: int, sender: bool = True):
        """Initialize the unicast class.

        Args:
            host (str): The host to send and receive messages.
            port (int): The port to send and receive messages.
            sender (bool, optional): Whether the unicast object is used for sending or receiving. Defaults to True.
        """
        self.host = host
        self.port = port if isinstance(port, int) else int(port)
        self.unicast_address = (self.host, self.port)

        self.sender = sender
        self.socket = None

        # Create the socket for unicast receiver
        if sender:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        else:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.bind(self.unicast_address)

    def send(self, message: str) -> None:
        """Send a message to the unicast host.

        Args:
            message (str): The message to send.
        """
        assert self.sender, "The unicast object is not a sender."
        self.socket.sendto(message.encode(), self.unicast_address)

    def receive(self, buffer_size: int = 1024) -> (bytes, str):
        """Receive a message from the unicast host.

        Args:
            buffer_size (int): The buffer size for the received message. Defaults to 1024.

        Returns:
            bytes: The received message.
            str: The address of the sender.
        """
        assert not self.sender, "The unicast object is not a receiver."
        return self.socket.recvfrom(buffer_size)
