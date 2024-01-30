from operator import itemgetter
from typing import Optional

from ipaddress import IPv4Address
import socket

import struct
import os

from typing import Optional
from communication.messages.total_ordering_isis.agreed_seq import MessageAgreedSequence
from communication.messages.total_ordering_isis.isis_message_with_counter import MessageIsisWithCounter
from communication.messages.total_ordering_isis.proposed_seq import MessageProposedSequence
from communication.unicast import Unicast
from constant.communication import(HEADER_AUCTION_BID)
# === Constants ===
from constant import BUFFER_SIZE


class Multicast:
    """Multicast class for sending and receiving multicast messages.

    This class implements a reliable, totally ordered multicast protocol.
    It is based on the ISIS algorithm.
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
        self._socket: socket.socket = None

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
        #TODO: The following send should only happen after the message went throuth the ISISProcess.
        #      So the task is to implement the process here and then send the message away with the follwing mc.send.
        mc.send(message)
        mc.close()

#Following class cannot be implemented in another .py, since the following class depends on the Multicast Class
#and the Multicast class depends on the following class. This prevents an circular import.
class ISISProcess:
    """ISISProcess class

    This class implements the ISIS algorithm.
    """

    def __init__(self):
        self.sequence_id = 0
        self.counter = 0
        self.holdback_queue = []
        self.suggested_sequence_list = []
        self.sender_id = int(str(Multicast.getIpAddress()).split(".")[3])
    
    def get_sequence_number(self, holdback_message: dict) -> int:
        """get_sequence_number returns the 'proposed_sequence_number' value

        Args:
            message (dict): A message element from the holdback queue.

        Returns:
            int: The proposed sequence number of the message.
        """
        return holdback_message['proposed_sequence_number']
    
    def shift_to_head(self, holdback_queue: list, holdback_message: dict):
        """shift_to_head shifts an item from the holdback queue to the head of list

        Args:
            message (dict): A message element from the holdback queue.
        """
        if holdback_message in holdback_queue:
            index_to_shift = holdback_queue.index(holdback_message)
            holdback_queue.pop(index_to_shift)
            holdback_queue.insert(0, holdback_message)

    def organize_holdback_queue(self):
        """organize_holdback_queue should be called on addition to holdback_queue or changing of element in holdback_queue"""
        # Sort the holdback queue ascending like in paper
        self.holdback_queue.sort(key=self.get_sequence_number)

        # If two sequence numbers are the same then place any undeliverable messages at the head 
        # to break further ties place message with smallest suggesting process # at the head end if
        has_same_tow_sequence_number = any(
            msg1['proposed_sequence_number'] == msg2['proposed_sequence_number']
            for i, msg1 in enumerate(self.holdback_queue)
            for j, msg2 in enumerate(self.holdback_queue[i + 1:])
            )   

        if has_same_tow_sequence_number: 
            undeliverable_messages = [msg for msg in self.holdback_queue if msg['status'] == 'undeliverable']
            if undeliverable_messages:
                self.shift_to_head(self.holdback_queue, undeliverable_messages[0])

            smallest_suggesting_process = min(self.suggested_sequence_list, key=lambda x: x[1])
            message_with_smallest_suggesting_process = next(
                (msg for msg in self.holdback_queue if msg['node_suggesting_sequence_id'] == smallest_suggesting_process),
                None
            )

            if message_with_smallest_suggesting_process:
                self.shift_to_head(self.holdback_queue, message_with_smallest_suggesting_process)

        # TODO: While message at head of queue has status deliverable do deliver the message at the head of the queue remove this message from the queueend while
        while self.holdback_queue[0]['status'] == 'deliverable':
            # TODO: deliver (execute action of) the message at the head of the queue
            self.holdback_queue.pop(0)

    def multicast_message_to_all(self, message: bytes, group: IPv4Address, port: int):
        """multicast_message_to_all should be called when a message is multicasted (in our case, when a bid is done).

        Args:
            message_content (str): The message_content to multicast.
            groupt (IPv4Address): The multicast group which should receive the message.
            port (port): The port of the multicast group.
        """
        # Counter represents the message_id
        self.counter += 1
        # Define message with header and multicast it
        isis_message_with_counter = MessageIsisWithCounter(message=message, counter=self.counter)
        Multicast.qsend(message=isis_message_with_counter, group=group, port=port)


    def on_receive_message_send_sequence_id_save_message_to_holdback_queue(self, message_content: str, message_id: int, received_sender_id: int, host: IPv4Address, port: int):
        """on_receive_message_send_sequence_id_save_message_to_holdback_queue should be called when MessageIsisWithCounter is received.

        TODO: This function should inside an if cause which checks for incoming bid. 
        """
        self.sequence_id += 1
        sequence_id_message = MessageProposedSequence(proposed_sequence=self.sequence_id)
        Unicast.qsend(message=sequence_id_message, host=host, port=port)
        self.holdback_queue.append({
            'message': message_content,
            'message_id': message_id,
            'received_sender_id': received_sender_id,
            'proposed_sequence_number': self.sequence_id,
            'process_suggesting_sequence_id': self.sender_id,
            'status': 'undeliverable'
        })
        self.organize_holdback_queue()

    def send_final_priority(self, message_id: int, sender_id: int, multicast_group: IPv4Address, port: int):
        """send_proposed_priority should be called when a MessageProposedSequence is received.

        TODO: This function should inside an if cause which checks if proposed sequence should be send.
        """
        #message, address = self.receiver.receive()
        # message[1] is sequence_id of sender and address[0] is sender_id
        self.suggested_sequence_list.append((message_id, int(str(sender_id).split('.')[3])))
        
        # TODO: Count members of multicast group and check if we have received sequence number from all processes.

        # Then extract highest squence number with received_sender_id from suggested_sequence_list. 
        # choose smallest possible value for suggested_node if there are multiple suggesting this sequence
        max_sequence_number = max(self.suggested_sequence_list, key=itemgetter(0))[0]
        max_sequence_tuple = max(self.suggested_sequence_list)
        for sequence_tuple in self.suggested_sequence_list:
            if sequence_tuple[0] == max_sequence_number:
                if sequence_tuple < max_sequence_tuple:
                    max_sequence_tuple = sequence_tuple
        # messagge[0] is the actual message id in this following line
        message_message_id_with_s_id_and_seq_id = MessageAgreedSequence(message_id=message_id, 
                                                                        sender_id=sender_id, 
                                                                        sequence_id=max_sequence_number[0], 
                                                                        sender_id_from_sequence_id=max_sequence_number[1]
                                                                        )
        Multicast.qsend(message_id=message_message_id_with_s_id_and_seq_id, group=multicast_group, port=port)
        # TODO: end if

    def put_final_sequence(self, message: bytes):
        """put_final_sequence should be called when the final proposed sequence should be put into the hold_back_queue.

        TODO: This function should inside an if cause which checks for incoming messages in this format.
        """

        #message, address = self.receiver.receive()
        # message[2] is the received sender_sequence
        self.sequence_id = max(self.sequence_id, message[2])
        for message_in_dict in self.holdback_queue:
            #message[0] is the received message_id and message[0] is the received sender_id
            if (message_in_dict['message_id'] == message[0]) and (message_in_dict['received_sender_IP'] == message[1]):
                # message[2] is the received sequence_id
                message_in_dict['proposed_sequence_number'] = message[2]
                # message[3] is the received sequence_id
                message_in_dict['process_suggesting_sequence_id'] = message[3]
                message_in_dict['status'] = 'deliverable'

        self.organize_holdback_queue()