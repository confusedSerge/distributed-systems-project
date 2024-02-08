from typing import Optional

from ipaddress import IPv4Address
import socket
import struct

from multiprocessing import Process, Queue, Manager, Event as ProcessEvent
from multiprocessing.synchronize import Event

from time import sleep

# === Custom Modules ===

from .messages import (
    MessageSchema,
    MessageReliableMulticast,
)

from util import generate_message_id

# === Constants ===

from constant import USERNAME, BUFFER_SIZE, HEADER_RELIABLE_MULTICAST


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


class RMulticast:
    """RMulticast class for sending and receiving reliable messages over multicast.

    This class implements a R-Multicast over UDP.
    The R-Multicast is a reliable multicast protocol using the IP protocol and UDP.
    This allows to simplify the multicasting, else needed to use the ReliableUnicast class to send reliable 1-to-1 messages.
    """

    def __init__(
        self,
        group: IPv4Address,
        port: int,
        timeout: Optional[int] = None,
        sequence_number: int = 0,
        client: bool = False,
    ):
        """Initialize the R-Multicast class.

        Args:
            group (IPv4Address): The multicast group to send and receive messages.
            port (int): The port to send and receive messages.
            timeout (Optional[int], optional): The timeout for receiving messages. Defaults to None, which does not trigger a timeout.
            sequence_number (int, optional): The initial sequence number to use. This is used for reinstating a previous sequence number. Defaults to 0.
        """
        # Device Identification
        self._sender_id: str = USERNAME + ("::CLIENT" if client else "::SERVER")

        # Basic setup
        self._group: IPv4Address = group
        self._port: int = port
        self._timeout: Optional[int] = timeout

        self._manager = Manager()
        self._exit: Event = ProcessEvent()

        # R-Multicast sender setup
        self._sequence_number: int = sequence_number
        self._multicast_sender: Multicast = Multicast(
            group=group, port=port, sender=True
        )
        self._received_messages: set[str] = set()
        self.sequence_to_messages = self._manager.dict()

        # R-Multicast receiver setup
        self.delivery_queue: Queue = Queue()  # where the messages are delivered
        self.retransmission_queue: Queue = (
            Queue()
        )  # sequence number of the message to be retransmitted
        self.acknowledgement_queue: Queue = (
            Queue()
        )  # tuple of (sender_id, sequence_number, true) to be acknowledged

        self._receiver: Process = Process(
            target=self._receive,
            args=(
                self.delivery_queue,
                self.retransmission_queue,
                self.acknowledgement_queue,
            ),
        )
        self._receiver.start()

        # Retransmission setup
        self._retransmission: Process = Process(
            target=self.retransmit,
            args=(self.retransmission_queue, self.sequence_to_messages),
        )
        self._retransmission.start()

    def send(self, payload: bytes) -> None:
        """Send an R-Multicast message to the multicast group.

        Args:
            message (bytes): payload of the message.
        """
        ack_messages: list[tuple[str, int, bool]] = []
        while not self.acknowledgement_queue.empty():
            ack_messages.append(self.acknowledgement_queue.get())

        message = MessageReliableMulticast(
            _id=generate_message_id(),
            sender=self._sender_id,
            b_sequence_number=self._sequence_number,
            payload=payload.decode(),
            acknowledgements=ack_messages,
        )
        # Add the message to the received messages, as sockets do not receive their own messages
        self._received_messages.add(message._id)
        self.sequence_to_messages[self._sequence_number] = message
        self._multicast_sender.send(message.encode())
        self._sequence_number += 1

    def deliver(self) -> tuple[bytes, tuple[IPv4Address, int]]:
        """Deliver the next R-Multicast message from the delivery queue.

        Returns:
            tuple[bytes, tuple[IPv4Address, int]]: The payload of the message and the sender address.
        """
        try:
            message, address = self.delivery_queue.get(timeout=self._timeout)
            if message._id not in self._received_messages:
                self._multicast_sender.send(message.encode())
                self._received_messages.add(message._id)

            return message.payload, address
        except:
            raise TimeoutError(f"Timeout of {str(self._timeout)} seconds reached.")

    def close(self) -> None:
        """Close the R-Multicast sender and receiver."""
        self._exit.set()
        self._receiver.join()
        self._retransmission.join()
        self._multicast_sender.close()

    # === Receiver ===

    def _receive(
        self,
        delivery_queue: Queue,
        retransmission_queue: Queue,
        acknowledgement_queue: Queue,
    ):
        """Receive R-Multicast messages from the multicast group.

        This is handled in a separate process, where messages ready to be delivered are put into the delivery_queue.

        Args:
            delivery_queue (Queue): The queue to put the received messages.
        """
        # Initialize the multicast receiver
        _peer_sequence_numbers: dict[str, int] = {}
        _multicast_receiver: Multicast = Multicast(
            group=self._group, port=self._port, timeout=1
        )
        # address of initial sender (encoded in message) -> list of (sequence number, message)
        _holdback_queue: dict[str, list[tuple[int, MessageReliableMulticast]]] = {}

        # Receive messages
        while not self._exit.is_set():
            try:
                message, _ = _multicast_receiver.receive()
            except TimeoutError:
                continue

            # Validate the message (own address is already ignored by socket implementation)
            if not MessageSchema.of(HEADER_RELIABLE_MULTICAST, message):
                continue

            decoded_message = MessageReliableMulticast.decode(message)
            if decoded_message.sender == self._sender_id:
                continue  # Ignore own messages

            # Initialize the peer if not present
            self._initialize_peer(
                decoded_message.sender, _peer_sequence_numbers, _holdback_queue
            )

            # Manage the received message
            self._manage_message(
                delivery_queue, _peer_sequence_numbers, _holdback_queue, decoded_message
            )

            self._process_acknowledgements(
                _peer_sequence_numbers,
                acknowledgement_queue,
                retransmission_queue,
                decoded_message,
            )

            # Check the holdback queue for possible messages to deliver
            self._holdback_queue_delivery(
                delivery_queue,
                _peer_sequence_numbers,
                _holdback_queue,
                decoded_message,
            )

        # Close the multicast receiver
        _multicast_receiver.close()

    def retransmit(
        self,
        retransmission_queue: Queue,
        sent_messages,
    ):
        """Retransmit the messages from the retransmission queue.

        Args:
            retransmission_queue (Queue): The queue for the retransmissions.
            sent_messages (DictProxy[str, MessageReliableMulticast]): The sent messages to look up the message to retransmit.
        """
        while not self._exit.is_set():
            try:
                sequence_number = retransmission_queue.get(timeout=self._timeout)
                message = sent_messages.get(sequence_number)
                if message:
                    self._multicast_sender.send(message.encode())
            except:
                continue

    # === Helper Functions ===

    def _initialize_peer(
        self,
        sender: str,
        _peer_sequence_numbers: dict[str, int],
        _holdback_queue: dict[str, list[tuple[int, MessageReliableMulticast]]],
    ):
        """Initialize the peer in the sequence numbers and holdback queue.

        Args:
            sender (str): The sender of the message.
            _peer_sequence_numbers (dict[str, int]): The sequence number of the peers.
            _holdback_queue (dict[str, list[tuple[int, MessageReliableMulticast]]]): The holdback queue for the peers.
        """
        if sender not in _peer_sequence_numbers:
            _peer_sequence_numbers[sender] = -1
            _holdback_queue[sender] = []

    def _process_acknowledgements(
        self,
        _peer_sequence_numbers: dict[str, int],
        acknowledgement_queue: Queue,
        retransmission_queue: Queue,
        message: MessageReliableMulticast,
    ):
        """Process the acknowledgements of the received message.

        Args:
            _peer_sequence_numbers (dict[str, int]): The sequence number of the peers.
            acknowledgement_queue (Queue): The queue for the acknowledgements.
            retransmission_queue (Queue): The queue for the retransmissions.
            message (MessageReliableMulticast): The received message.
        """
        acknowledgement_queue.put((message.sender, message.b_sequence_number, True))

        for sender, sequence_number, ack in message.acknowledgements:
            if sender == self._sender_id:
                if not ack:
                    retransmission_queue.put(sequence_number)
            elif (
                sender not in _peer_sequence_numbers
                or sequence_number > _peer_sequence_numbers[sender]
            ):
                for needed in range(sequence_number - _peer_sequence_numbers[sender]):
                    acknowledgement_queue.put((sender, sequence_number - needed, False))

    def _manage_message(
        self,
        delivery_queue: Queue,
        _peer_sequence_numbers: dict[str, int],
        _holdback_queue: dict[str, list[tuple[int, MessageReliableMulticast]]],
        message: MessageReliableMulticast,
    ):
        """Manage the received message.

        The behavior is the same as normal B-Multicast.

        Args:
            delivery_queue (Queue): The queue to put the received messages, if ready to deliver.
            _peer_sequence_numbers (dict[tuple[IPv4Address, int], int]): The sequence number of the peers.
            _holdback_queue (dict[tuple[IPv4Address, int], list[tuple[int, bytes]]]): The holdback queue for the peers.
            message (bytes): The received message.
        """
        peer_sequence_number = _peer_sequence_numbers.get(message.sender, -1)

        # Receive message
        if message.b_sequence_number == peer_sequence_number + 1:
            delivery_queue.put((message, message.sender))
            _peer_sequence_numbers[message.sender] = peer_sequence_number + 1
        else:
            _holdback_queue[message.sender].append((message.b_sequence_number, message))

    def _holdback_queue_delivery(
        self,
        delivery_queue: Queue,
        _peer_sequence_numbers: dict[str, int],
        _holdback_queue: dict[str, list[tuple[int, MessageReliableMulticast]]],
        message: MessageReliableMulticast,
    ):
        """Check the holdback queue for possible messages to deliver.

        Args:
            delivery_queue (Queue): The queue to put the received messages, if ready to deliver.
            _peer_sequence_numbers (dict[tuple[IPv4Address, int], int]): The sequence number of the peers.
            _holdback_queue (dict[tuple[IPv4Address, int], list[tuple[int, MessageReliableMulticast]]]): The holdback queue for the peers.
        """
        if message.sender not in _holdback_queue:
            return

        holdback_queue_for_address = sorted(
            _holdback_queue[message.sender], key=lambda x: x[0]
        )
        for sequence_number, message in holdback_queue_for_address:
            if sequence_number == _peer_sequence_numbers[message.sender] + 1:
                delivery_queue.put((message, message.sender))
                _holdback_queue[message.sender].remove((sequence_number, message))
                _peer_sequence_numbers[message.sender] += 1
            else:
                break
