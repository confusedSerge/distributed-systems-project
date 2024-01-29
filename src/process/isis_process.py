from audioop import mul
from email import message
from ipaddress import IPv4Address
from communication.messages.total_ordering_isis import MessageIsisWithCounter
from communication.messages.total_ordering_isis import MessageProposedSequence
from communication.messages.total_ordering_isis import MessageAgreedSequence
from communication.multicast import Multicast
from communication.unicast import Unicast
from constant.communication import multicast as constant_multicast
from operator import itemgetter

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

        #TODO: implement processing messages from head of the queue and removing them after processed.
