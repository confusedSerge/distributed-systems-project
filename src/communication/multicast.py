from ipaddress import IPv4Address
import socket
import struct
import os

from typing import Optional
from communication.messages.message_schema import MessageSchema
from constant.communication import(HEADER_AUCTION_BID)
from messages import MessageIsis, MessageProposedSequence, MessageAgreedSequence
from process.isis_process import ISISProcess


class Multicast:
    """Multicast class for sending and receiving multicast messages.

    This class implements a reliable, totally ordered multicast protocol.
    It is based on the ISIS algorithm.

    TODO: Implement the ISIS algorithm. Currently, this class has basic UDP Multicast functionality.
    """

    def __init__(
        self,
        group: IPv4Address,
        port: int,
        sender: bool = False,
        ttl: int = 32,
        timeout: Optional[int] = None,
    ):
        """Initialize the multicast class.

        Args:
            group (IPv4Address): The multicast group to send and receive messages.
            port (int): The port to send and receive messages.
            sender (bool, optional): Whether the multicast object is used for sending or receiving. Defaults to False.
            ttl (int, optional): The time to live for the multicast messages. Defaults to 32.
            timeout (Optional[int], optional): The timeout for receiving messages. Defaults to None, which does not trigger a timeout.
        """
        assert isinstance(group, IPv4Address), "The group must be an IPv4Address."
        assert group.is_multicast, "The group must be a multicast address."

        assert isinstance(port, int), "The port must be an integer."

        self._address: IPv4Address = group
        self._port: int = port if isinstance(port, int) else int(port)
        self._address_port: tuple[str, int] = (str(self._address), self._port)

        self._sender: bool = sender
        self._socket: socket.socket = None

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
                struct.pack(
                    "4sl", socket.inet_aton(str(self._address)), socket.INADDR_ANY
                ),
            )
            self._socket.settimeout(self._timeout) if self._timeout else None
            self._socket.bind(self._address_port)

    def getIpAddress(self) -> str:
        """Get IpAddr of own instance."""
        gw = os.popen("ip -4 route show default").read().split()
        self._socket.connect((gw[2], 0))

        return self._socket.getsockname()[0]

    def send(self, message: bytes) -> None:
        """Send a message to the multicast group.

        Args:
            message (bytes): The message to send in bytes.
        """
        assert self._sender, "The multicast object is not a sender."

        if MessageSchema.of(HEADER_AUCTION_BID, message):
            #start the isis algo
            isis_process = ISISProcess(self)
            isis_process.run() #TODO
        else:
            self._socket.sendto(message, self._address_port)

    def send_message_with_counter(self, message: bytes, counter: int, sender_id: int) -> None:
        """Send a message tuple to the multicast group.

        Args:
            message (bytes): The message to send in bytes.
            counter:
            sender_ip:
        """
        isis_message: MessageIsis = MessageIsis(_id = counter, message_content = message, sendeissr_ip = sender_id)
        assert self._sender, "The multicast object is not a sender."
        self._socket.sendto(isis_message, self._address_port)    

    def send_message_id_with_seq_id(self, message_id: int, sequence_id: int) -> None:
        """Send a MessageProposedSequence to the sender of the inital msg it schould be unicast #TODO

        Args:
            message_id:
            sender_ip:
        """
        assert self._sender, "The multicast object is not a sender."
        msg_with_seq_num : MessageProposedSequence = MessageProposedSequence(_id = message_id,proposed_sequence = sequence_id)
        self._socket.sendto(msg_with_seq_num, self._address_port)  

    def send_message_id_with_s_id_and_seq_id(self, message_id: int, sender_id: int, sequence_id: int, senderid_from_sequence_id: int) -> None:
        """Send a MessageAgreedSequence to the multicast group.

        Args:
            message (bytes): The message to send in bytes.
            sender_ip:

        """
        assert self._sender, "The multicast object is not a sender."
        msg_with_agreed_seq: MessageAgreedSequence = MessageAgreedSequence(_id = message_id, sender_id = sender_id,sequence_id = sequence_id, senderid_from_sequence_id = senderid_from_sequence_id )
        self._socket.sendto(msg_with_agreed_seq, self._address_port)    

    def receive(self, buffer_size: int = 1024) -> (bytes, tuple[str, int]):
        """Receive a message from the multicast group.

        Args:
            buffer_size (int): The buffer size for the received message. Defaults to 1024.

        Returns:
            bytes: The received message.
            tuple[str, int]: The sender address and port.

        Raises:
            socket.timeout: If the timeout is set and no message was received.
        """
        assert not self._sender, "The multicast object is not a receiver."
        return self._socket.recvfrom(buffer_size)

    def close(self) -> None:
        """Close the multicast socket."""
        self._socket.close()

    @staticmethod
    def qsend(message: bytes, group: IPv4Address, port: int, ttl: int = 32) -> None:
        """Send a message to the multicast group.

        Args:
            message (bytes): The message to send in bytes.
            group (IPv4Address): The multicast address to send and receive messages.
            port (int): The port to send and receive messages.
            ttl (int, optional): The time to live for the multicast messages. Defaults to 32.
        """
        mc = Multicast(group, port, sender=True, ttl=ttl)
        mc.send(message)
        mc.close()
