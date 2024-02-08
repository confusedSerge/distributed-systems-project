from typing import Optional

from ipaddress import IPv4Address
import socket
import struct

from multiprocessing import Process, Queue, Event as ProcessEvent
from multiprocessing.synchronize import Event

# === Custom Modules ===

from .messages import (
    MessageSchema,
    MessageIsisMessage,
    MessageIsisProposedSequence,
    MessageIsisAgreedSequence,
)

from .unicast import Unicast

from util import generate_message_id, Timeout

# === Constants ===

from constant import (
    BUFFER_SIZE,
    HEADER_ISIS_MESSAGE,
    HEADER_ISIS_MESSAGE_PROPOSED_SEQ,
    HEADER_ISIS_MESSAGE_AGREED_SEQ,
)


class Multicast:
    """Multicast class for sending and receiving multicast messages.

    This class implements a basic multicast over IP using the UDP protocol.
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

        # Address
        self._group: IPv4Address = group
        self._port: int = port if isinstance(port, int) else int(port)
        self._address: tuple[str, int] = (str(self._group), self._port)

        # Options
        self._sender: bool = sender
        self._timeout: Optional[int] = timeout

        # Create the socket for multicast sender/receiver
        if sender:
            self._socket: socket.socket = socket.socket(
                socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP
            )
            self._socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)
        else:
            self._socket: socket.socket = socket.socket(
                socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP
            )
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            self._socket.setsockopt(
                socket.IPPROTO_IP,
                socket.IP_ADD_MEMBERSHIP,
                struct.pack(
                    "4sl", socket.inet_aton(str(self._group)), socket.INADDR_ANY
                ),
            )
            self._socket.settimeout(self._timeout) if self._timeout else None
            self._socket.bind(self._address)

    def send(self, message: bytes) -> None:
        """Send a message to the multicast group.

        Args:
            message (bytes): The message to send in bytes.
        """
        assert self._sender, "The multicast object is not a sender."
        self._socket.sendto(message, self._address)

    def receive(
        self, buffer_size: int = BUFFER_SIZE
    ) -> tuple[bytes, tuple[IPv4Address, int]]:
        """Receive a message from the multicast group.

        Args:
            buffer_size (int): The buffer size for the received message. Defaults to BUFFER_SIZE.

        Returns:
            bytes: The received message.
            tuple[str, int]: The sender address and port.

        Raises:
            socket.timeout: If the timeout is set and no message was received.
        """
        assert not self._sender, "The multicast object is not a receiver."
        message, address = self._socket.recvfrom(buffer_size)
        return message, (IPv4Address(address[0]), address[1])

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


class IsisRMulticast:
    """IsisRMulticast class for sending and receiving ISIS messages over multicast.

    This class implements a basic ISIS multicast using R-Multicast over UDP.
    The R-Multicast is a reliable multicast protocol using the IP protocol and UDP.
    This allows to simplify the multicasting, else needed to use the ReliableUnicast class to send reliable 1-to-1 messages.
    """

    def __init__(self, group: IPv4Address, port: int, timeout: Optional[int] = None):
        """Initialize the ISIS multicast class.

        Args:
            group (IPv4Address): The multicast group to send and receive messages.
            port (int): The port to send and receive messages.
            timeout (Optional[int], optional): The timeout for receiving messages. Defaults to None, which does not trigger a timeout.
        """
        # Basic setup
        self._group: IPv4Address = group
        self._port: int = port
        self._timeout: Optional[int] = timeout

        self._exit: Event = ProcessEvent()

        # B-Multicast sender setup
        self._sequence_number: int = 0
        self._multicast_sender: Multicast = Multicast(
            group=group, port=port, sender=True
        )

        # B-Multicast receiver setup
        self.delivery_queue: Queue = Queue()
        self._receiver: Process = Process(
            target=self._receive,
            args=(self.delivery_queue, (self._group, self._port)),
        )
        self._receiver.start()

    def send(self, message: bytes) -> None:
        """Send an ISIS message to the multicast group.

        Args:
            message (bytes): payload of the message.
        """
        isis_message = MessageIsisMessage(
            _id=generate_message_id(),
            payload=message.decode(),
            b_sequence_number=self._sequence_number,
        )
        self._multicast_sender.send(isis_message.encode())
        self._sequence_number += 1

    def deliver(self) -> tuple[bytes, tuple[IPv4Address, int]]:
        """Deliver the ISIS messages from the delivery queue.

        Returns:
            tuple[bytes, tuple[IPv4Address, int]]: The ISIS message and the address of the sender.
        """
        try:
            return self.delivery_queue.get(timeout=self._timeout)
        except:
            raise TimeoutError(f"Timeout of {str(self._timeout)} seconds reached.")

    def close(self) -> None:
        """Close the ISIS multicast sender and receiver."""
        self._exit.set()
        self._receiver.join()
        self._multicast_sender.close()

    # === Receiver ===

    def _receive(
        self, delivery_queue: Queue, ignore_address: tuple[IPv4Address, int]
    ) -> None:
        """Receive ISIS messages from the multicast group.

        This is handled in a separate process, where messages ready to be delivered are put into the delivery_queue.

        Args:
            delivery_queue (Queue): The queue to put the received messages.
            ignore_address (tuple[IPv4Address, int]): The address to ignore. Should be the address of the own sender.
        """
        # Initialize the multicast receiver
        _peer_sequence_numbers: dict[tuple[IPv4Address, int], int] = {}
        _multicast_receiver: Multicast = Multicast(
            group=self._group, port=self._port, timeout=1
        )
        # address -> list of (sequence number, message)
        _holdback_queue: dict[tuple[IPv4Address, int], list[tuple[int, bytes]]] = {}

        # Receive ISIS messages
        while not self._exit.is_set():
            try:
                message, address = _multicast_receiver.receive()
            except TimeoutError:
                continue

            # Validate the message
            if not MessageSchema.of(HEADER_ISIS_MESSAGE, message):
                continue

            # Decode the message
            self._manage_message(
                delivery_queue,
                _peer_sequence_numbers,
                _holdback_queue,
                message,
                address,
            )

            # Check the holdback queue for possible messages to deliver

            self._holdback_queue_delivery(
                delivery_queue, _peer_sequence_numbers, _holdback_queue, address
            )

        # Close the multicast receiver
        _multicast_receiver.close()

    # === Helper Functions ===

    def _manage_message(
        self,
        delivery_queue: Queue,
        _peer_sequence_numbers: dict[tuple[IPv4Address, int], int],
        _holdback_queue: dict[tuple[IPv4Address, int], list[tuple[int, bytes]]],
        message: bytes,
        address: tuple[IPv4Address, int],
    ):
        """Manage the received ISIS message.

        The behavior is the same as normal B-Multicast.

        Args:
            delivery_queue (Queue): The queue to put the received messages, if ready to deliver.
            _peer_sequence_numbers (dict[tuple[IPv4Address, int], int]): The sequence number of the peers.
            _holdback_queue (dict[tuple[IPv4Address, int], list[tuple[int, bytes]]]): The holdback queue for the peers.
            message (bytes): The received message.
            address (tuple[IPv4Address, int]): The address of the sender.
        """
        received_message = MessageIsisMessage.decode(message)
        peer_sequence_number = _peer_sequence_numbers.get(address, -1)

        # Receive message
        if received_message.b_sequence_number == peer_sequence_number + 1:
            delivery_queue.put((received_message.payload.encode(), address))
            _peer_sequence_numbers[address] = peer_sequence_number + 1
        else:
            _holdback_queue[address].append(
                (
                    received_message.b_sequence_number,
                    received_message.payload.encode(),
                )
            )

    def _holdback_queue_delivery(
        self,
        delivery_queue: Queue,
        _peer_sequence_numbers: dict[tuple[IPv4Address, int], int],
        _holdback_queue: dict[tuple[IPv4Address, int], list[tuple[int, bytes]]],
        address: tuple[IPv4Address, int],
    ):
        """Check the holdback queue for possible messages to deliver.

        Args:
            delivery_queue (Queue): The queue to put the received messages, if ready to deliver.
            _peer_sequence_numbers (dict[tuple[IPv4Address, int], int]): The sequence number of the peers.
            _holdback_queue (dict[tuple[IPv4Address, int], list[tuple[int, bytes]]]): The holdback queue for the peers.
            address (tuple[IPv4Address, int]): The address of the sender.
        """
        if address not in _holdback_queue:
            return

        holdback_queue_for_address = sorted(
            _holdback_queue[address], key=lambda x: x[0]
        )
        for sequence_number, payload in holdback_queue_for_address:
            if sequence_number == _peer_sequence_numbers[address] + 1:
                delivery_queue.put((payload, address))
                _peer_sequence_numbers[address] += 1
                _holdback_queue[address].remove((sequence_number, payload))
            else:
                break
