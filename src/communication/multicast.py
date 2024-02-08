from typing import Optional

from ipaddress import IPv4Address
import socket
import struct

from multiprocessing import Process, Queue, Manager, Event as ProcessEvent
from multiprocessing.synchronize import Event

from time import time
from uuid import uuid4

# === Custom Modules ===

from .messages import (
    MessageSchema,
    MessageReliableMulticast,
    MessageIsisMessage,
    MessageIsisProposedSequence,
    MessageIsisAgreedSequence,
)
from .unicast import ReliableUnicast

from util import generate_message_id

# === Constants ===

from constant import (
    USERNAME,
    BUFFER_SIZE,
    HEADER_RELIABLE_MULTICAST,
    HEADER_ISIS_MESSAGE,
    HEADER_ISIS_MESSAGE_PROPOSED_SEQ,
    HEADER_ISIS_MESSAGE_AGREED_SEQ,
    TIMEOUT_HEARTBEAT,
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
        self._sender_id: str = (
            USERNAME + ("::CLIENT::" if client else "::SERVER::") + str(uuid4())
        )

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

            return message.payload.encode(), address
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


class AdjustedIsisRMulticast:
    """Adjusted ISIS R-Multicast class for sending and receiving reliable messages over multicast.

    This class implements an adjusted ISIS protocol for reliable total order multicast.
    Adjusted is due to the changes in the protocol to fit 'open' multicast groups.

    This 'open' group can be seen when a client sends messages inside an auction group.
    Also, this open group is not actually open, as clients do join the group.
    However, a client does not participate in ordering messages of other clients.
    Only replicas participate in ordering messages of clients and replicas.

    This allows for a more efficient protocol, as clients do not need to participate in ordering messages.
    Futhermore, there is no need for an internal heartbeat, as replicas are managed by the leader with heartbeats.
    This allows to upper bound responses to 2 * HEARTBEAT_TIMEOUT, as at that point, a replica is considered dead.
    Also, a client non agreed message can be removed after 2 * HEARTBEAT_TIMEOUT, as at this point, the client can be considered dead if it did not send the agreed message.
    This holds only true, if this is used in the context of the auction group, even when the sender is a replica.

    Therefore, there exists a switch in the protocol, to remove ordering participation.
    """

    def __init__(
        self,
        group: IPv4Address,
        port: int,
        timeout: Optional[int] = None,
        sequence_number: int = 0,
        client: bool = False,
    ):
        """Initialize the ISIS R-Multicast class.

        Args:
            group (IPv4Address): The multicast group to send and receive messages.
            port (int): The port to send and receive messages.
            timeout (Optional[int], optional): The timeout for receiving messages. Defaults to None, which does not trigger a timeout.
            sequence_number (int, optional): The initial sequence number to use for R-Multicast. This is used for reinstating a previous sequence number. Defaults to 0.
        """
        self._address = (group, port)
        self._timeout = timeout
        self.b_sequence_number = sequence_number

        self._exit: Event = ProcessEvent()

        # ISIS setup
        self._client = client
        self._proposed_sequence = 0
        self._agreed_sequence = 0
        self.send_queue = Queue()
        self.delivery_queue: Queue = Queue()

        # Start the sender and receiver processes
        self._sender = Process(target=self._send, args=(self.send_queue,))
        if not client:
            self._receiver = Process(target=self._receive, args=(self.delivery_queue,))

        self._sender.start()
        if not client:
            self._receiver.start()

    def send(self, payload: bytes) -> None:
        """Send an ISIS R-Multicast message to the multicast group.

        Args:
            message (bytes): payload of the message.
        """
        if self._exit.is_set():
            return

        self.send_queue.put(payload)

    def deliver(self) -> tuple[bytes, tuple[IPv4Address, int]]:
        """Deliver the next ISIS R-Multicast message from the delivery queue.

        Returns:
            tuple[bytes, tuple[IPv4Address, int]]: The payload of the message and the sender address.
        """
        assert not self._client, "The ISIS R-Multicast object cannot deliver messages."
        try:
            message, address = self.delivery_queue.get(timeout=self._timeout)
            return message.payload.encode(), address
        except:
            raise TimeoutError(f"Timeout of {str(self._timeout)} seconds reached.")

    def close(self) -> None:
        """Close the ISIS R-Multicast sender and receiver."""
        self._exit.set()
        self._sender.join()
        if not self._client:
            self._receiver.join()

    # === Sender ===

    def _send(self, send_queue: Queue):
        """Process for sending totally ordered messages.

        Args:
            send_queue (Queue): The queue for the messages to send.
        """
        # Initialize the multicast sender and unicast receiver
        multicast_sender = RMulticast(
            self._address[0],
            self._address[1],
            timeout=self._timeout,
            sequence_number=self.b_sequence_number,
            client=self._client,
        )
        unicast_receiver = ReliableUnicast(timeout=1)

        # Main sending loop
        while not self._exit.is_set() or not send_queue.empty():
            try:
                payload = send_queue.get(timeout=self._timeout)
            except:
                continue

            print("Sending message")

            # Build and send the message
            mid = self._send_message(
                multicast_sender,
                payload,
                (
                    str(unicast_receiver.get_address()[0]),
                    unicast_receiver.get_address()[1],
                ),
            )

            print(f"Waiting for proposed sequences for {mid}")

            # Wait for the proposed sequences
            largest_proposed_sequence = self._receive_proposed_sequences(
                mid, unicast_receiver
            )

            print(f"Received proposed sequences for {mid}: {largest_proposed_sequence}")

            # Send the agreed sequence
            self._send_agreed_sequence(mid, largest_proposed_sequence, multicast_sender)

            print(f"Sent agreed sequence for {mid}")

        print("Exiting sender")
        multicast_sender.close()
        unicast_receiver.close()
        print("Exited sender")

    def _send_message(
        self,
        multicast_sender: RMulticast,
        payload: bytes,
        reply_to: tuple[str, int],
    ) -> str:
        """Sends the initial message to the multicast group.

        Args:
            multicast_sender (RMulticast): The multicast sender to send the message.
            payload (bytes): The payload of the message.
            reply_to (tuple[str, int]): The address of the reliable unicast to reply to.

        Returns:
            str: The message ID of the sent message.
        """
        message = MessageIsisMessage(
            _id=generate_message_id(),
            payload=payload.decode(),
            reply_to=reply_to,
        )

        multicast_sender.send(message.encode())

        return message._id

    def _receive_proposed_sequences(
        self, mid: str, unicast_receiver: ReliableUnicast
    ) -> int:
        """Receive the proposed sequences from the replicas.

        Args:
            mid (str): The message ID of the message to receive the proposed sequences.
            unicast_receiver (ReliableUnicast): The reliable unicast receiver to receive the proposed sequences.

        Returns:
            int: The largest proposed sequence.
        """
        largest_proposed_sequence = 0
        heartbeat = time()
        while time() - heartbeat < 2 * TIMEOUT_HEARTBEAT:
            try:
                message, _ = unicast_receiver.receive()
            except TimeoutError:
                continue

            if (
                not MessageSchema.of(HEADER_ISIS_MESSAGE_PROPOSED_SEQ, message)
                or MessageSchema.get_id(message) != mid
            ):
                continue

            proposed_sequence = MessageIsisProposedSequence.decode(
                message
            ).proposed_sequence
            largest_proposed_sequence = max(
                largest_proposed_sequence, proposed_sequence
            )
        return largest_proposed_sequence

    def _send_agreed_sequence(
        self, mid: str, sequence: int, multicast_sender: RMulticast
    ) -> None:
        """Send the agreed sequence to the sender.

        Args:
            mid (str): The message ID of the message to send the agreed sequence.
            sequence (int): The agreed sequence to send.
            multicast_sender (RMulticast): The multicast sender to send the agreed sequence.
        """
        message = MessageIsisAgreedSequence(_id=mid, agreed_sequence=sequence)
        multicast_sender.send(message.encode())

    # === Receiver ===

    def _receive(self, delivery_queue: Queue):
        """Process for receiving totally ordered messages.

        Args:
            delivery_queue (Queue): The queue to put the received messages.
        """
        # Initialize the multicast receiver and unicast sender
        multicast_receiver: RMulticast = RMulticast(
            self._address[0],
            self._address[1],
            timeout=self._timeout,
            sequence_number=self.b_sequence_number,
            client=self._client,
        )
        unicast_sender: ReliableUnicast = ReliableUnicast()
        # message_id -> (proposed_sequence, is_agreed, message, arrival_time)
        holdback_queue: dict[str, tuple[int, bool, MessageIsisMessage, float]] = {}

        # Main receiving loop
        while not self._exit.is_set():
            try:
                message, _ = multicast_receiver.deliver()
            except:
                print(f"Exiting: {self._exit.is_set()}")
                continue
            arrival_time = time()

            print(f"Received message {message}")

            if not MessageSchema.of(
                HEADER_ISIS_MESSAGE, message
            ) and not MessageSchema.of(HEADER_ISIS_MESSAGE_AGREED_SEQ, message):
                print(f"Received message is not a ISIS message")
                print(MessageSchema.of(HEADER_ISIS_MESSAGE, message))
                print(MessageSchema.of(HEADER_ISIS_MESSAGE_AGREED_SEQ, message))
                continue

            if MessageSchema.of(HEADER_ISIS_MESSAGE, message):
                print(f"Received message {MessageSchema.get_id(message)}")
                self._receive_message(
                    message, unicast_sender, holdback_queue, arrival_time
                )
                print(f"Sent agreed sequence for {MessageSchema.get_id(message)}")
                continue

            if MessageSchema.get_id(message) not in holdback_queue:
                continue  # not a message, where you proposed a sequence

            print(f"Received agreed sequence for {MessageSchema.get_id(message)}")
            self._receive_agreed_sequence(message, holdback_queue)
            # sort the holdback queue by the agreed sequence
            holdback_queue = dict(
                sorted(
                    holdback_queue.items(),
                    key=lambda item: item[1][0],
                )
            )
            print(f"Delivering messages")
            self._deliver_messages(delivery_queue, holdback_queue, arrival_time)

        print("Exiting receiver")
        multicast_receiver.close()
        unicast_sender.close()
        print("Exited receiver")

    def _receive_message(
        self,
        message: bytes,
        unicast_sender: ReliableUnicast,
        holdback_queue: dict[str, tuple[int, bool, MessageIsisMessage, float]],
        arrival_time: float,
    ):
        """Receive a isis message and send the proposed sequence.

        Args:
            message (bytes): The received message.
            unicast_sender (ReliableUnicast): The reliable unicast sender to send the proposed sequence.
            holdback_queue (dict[str, tuple[int, bool, MessageIsisMessage, float]]): The holdback queue for messages.
            arrival_time (float): The arrival time of the message.
        """
        # Calculate the proposed sequence
        self._proposed_sequence = (
            max(self._proposed_sequence, self._agreed_sequence) + 1
        )

        print(f"proposed sequence {self._proposed_sequence}")

        # Send the proposed sequence
        isis_message = MessageIsisMessage.decode(message)
        proposed_sequence_message = MessageIsisProposedSequence(
            _id=isis_message._id, proposed_sequence=self._proposed_sequence
        )
        reply_to = (IPv4Address(isis_message.reply_to[0]), isis_message.reply_to[1])
        unicast_sender.send(proposed_sequence_message.encode(), reply_to)

        print(f"Sent proposed sequence {self._proposed_sequence}")

        # Add the message to the holdback queue
        holdback_queue[isis_message._id] = (
            self._proposed_sequence,
            False,
            isis_message,
            arrival_time,
        )

        print(f"Added message {isis_message._id} to holdback queue")

    def _receive_agreed_sequence(
        self,
        message: bytes,
        holdback_queue: dict[str, tuple[int, bool, MessageIsisMessage, float]],
    ):
        """Receive the agreed sequence and deliver the message.

        Args:
            message (bytes): The received message.
            holdback_queue (dict[int, tuple[MessageIsisMessage, bool]]): The holdback queue for messages.
        """
        # Calculate the agreed sequence
        agreed_sequence = MessageIsisAgreedSequence.decode(message).agreed_sequence
        self._agreed_sequence = max(self._agreed_sequence, agreed_sequence)

        print(f"Received agreed sequence {agreed_sequence}")

        # Update the message in the holdback queue
        message_id = MessageSchema.get_id(message)
        assert message_id in holdback_queue, "The message is not in the holdback queue."

        print(f"Updating message {message_id}")

        entry = holdback_queue[message_id]
        entry = (self._agreed_sequence, True, entry[2], entry[3])
        holdback_queue[message_id] = entry

    def _deliver_messages(
        self,
        delivery_queue: Queue,
        holdback_queue: dict[str, tuple[int, bool, MessageIsisMessage, float]],
        arrival_time: float,
    ):
        """Deliver the messages from the holdback queue.

        Args:
            delivery_queue (Queue): The queue to put the received messages.
            holdback_queue (dict[int, tuple[MessageIsisMessage, bool]]): The holdback queue for messages.
            arrival_time (float): The arrival time of the message.
        """
        print(f"Delivering messages: {holdback_queue}")
        ids_to_remove = []
        for message_id, (
            sequence,
            agreed,
            message,
            message_arrival_time,
        ) in holdback_queue.items():
            if agreed:
                print(f"Delivering message {message_id}")
                delivery_queue.put((message, message.reply_to))
                ids_to_remove.append(message_id)
            elif arrival_time - message_arrival_time > 2 * TIMEOUT_HEARTBEAT:
                print(f"Removing message {message_id}")
                ids_to_remove.append(message_id)
            else:
                print(f"Keeping message {message_id} as not agreed yet")
                break

        for message_id in ids_to_remove:
            holdback_queue.pop(message_id)
