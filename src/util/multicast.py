import socket
import struct
import os


class Multicast:
    """Multicast class for sending and receiving multicast messages.

    This class implements a reliable, totally ordered multicast protocol.
    It is based on the ISIS algorithm.

    TODO: Implement the ISIS algorithm. Currently, this class has basic UDP Multicast functionality.
    """

    def __init__(self, group: str, port: int, sender: bool = True, ttl: int = 1):
        """Initialize the multicast class.

        Args:
            group (str): The multicast group to send and receive messages.
            port (int): The port to send and receive messages.
            sender (bool, optional): Whether the multicast object is used for sending or receiving. Defaults to True.
            ttl (int, optional): The time to live for the multicast messages. Defaults to 1.
        """
        self.group = group
        self.port = port if isinstance(port, int) else int(port)
        self.multicast_group = (self.group, self.port)

        self.sender = sender
        self.socket = None

        # Create the socket for multicast sender
        if sender:
            self.socket = socket.socket(
                socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP
            )
            self.socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)
        # Create the socket for multicast receiver    
        else:  # Receiver
            self.socket = socket.socket(
                socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP
            )
            self.socket.bind(self.multicast_group)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.setsockopt(
                socket.IPPROTO_IP,
                socket.IP_ADD_MEMBERSHIP,
                struct.pack("4sl", socket.inet_aton(self.group), socket.INADDR_ANY),
            )
            
    def getIpAddress(self) -> str:
        """Get IpAddr of own instance."""
        gw = os.popen("ip -4 route show default").read().split()
        self.socket.connect((gw[2], 0))

        return self.socket.getsockname()[0]
    
    #TODO: Give correct names for multiple send and receive methods.

    def send(self, message: bytes) -> None:
        """Send a message to the multicast group.

        Args:
            message (bytes): The message to send in bytes.
        """
        assert self.sender, "The multicast object is not a sender."
        self.socket.sendto(message, self.multicast_group)

    def send(self, message: bytes, counter: int, sender_ip: str) -> None:
        """Send a message tuple to the multicast group.

        Args:
            message (bytes): The message to send in bytes.
            counter:
            sender_ip:
        """
        assert self.sender, "The multicast object is not a sender."
        self.socket.sendto((message, counter, sender_ip), self.multicast_group)    

    def send(self, message_id: int, sequence_id: int) -> None:
        """Send a message tuple to the multicast group.

        Args:
            message_id:
            sender_ip:
        """
        assert self.sender, "The multicast object is not a sender."
        self.socket.sendto((message_id, sequence_id), self.multicast_group)  

    def send(self, message_id: int, sender_ip: str, sequence_id: int, ip_from_sequence_id: str) -> None:
        """Send a message tuple to the multicast group.

        Args:
            message (bytes): The message to send in bytes.
            sender_ip:

        """
        assert self.sender, "The multicast object is not a sender."
        self.socket.sendto((message_id, sender_ip, sequence_id, ip_from_sequence_id), self.multicast_group)    

    def receive(self, buffer_size: int = 1024) -> (bytes, str):
        """Receive a message from the multicast group.

        Args:
            buffer_size (int): The buffer size for the received message. Defaults to 1024.

        Returns:
            bytes: The received message.
            str: The address of the sender.
        """
        assert not self.sender, "The multicast object is not a receiver."
        return self.socket.recvfrom(buffer_size)

    def close(self) -> None:
        """Close the multicast socket."""
        self.socket.close()
