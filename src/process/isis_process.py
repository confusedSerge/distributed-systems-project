from communication.multicast import Multicast
from communication.messages.isis_communication.isis_message import IsisMessage
from constant.communication import multicast as constant_multicast
from operator import itemgetter

class ISISProcess:
    """ISISProcess class

    This class implements the ISIS algorithm.

    """
    sender = Multicast(
        constant_multicast.DISCOVERY_GROUP,
        constant_multicast.DISCOVERY_PORT,
        sender=True,
        ttl=constant_multicast.DISCOVERY_TTL,
    )
    receiver = Multicast(
        constant_multicast.DISCOVERY_GROUP,
        constant_multicast.DISCOVERY_PORT,
        sender=False,
        ttl=constant_multicast.DISCOVERY_TTL,
    )

    def __init__(self):
        self.sequence_id = 0
        self.counter = 0
        self.holdback_queue = []
        self.suggested_sequence_list = []
        self.sender_id = int(self.sender.getIpAddress().split(".")[3])
        self.receiver_ip = self.receiver.getIpAddress()

    def multicast_message_to_all(self, isis_message: IsisMessage):
        """multicast_message_to_all should be called when a message is multicasted (in our case, when a bid is done).

        Args:
            message (Message): The message to multicast.
        """
        # Counter represents the message_id
        self.counter += 1
        self.sender.send_message_with_counter(isis_message.message_content, self.counter, self.sender_id)

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
            # TODO: deliver (do action of) the message at the head of the queue
            self.holdback_queue.pop(0)

    def on_receive_message_save_to_holdback_queue(self, message: bytes):
        """on_receive_message_save_to_holdback_queue should be called when a bid is received.

        TODO: This function should inside an if cause which checks for incoming bid. 
        """
        self.sequence_id += 1
        message, address = self.receiver.receive()
        self.sender.send_message_id_with_seq_id(message_id=message[1], sequence_id=self.sequence_id)
        self.holdback_queue.append({
            'message': message[0],
            'message_id': message[1],
            'received_sender_id': message[2],
            'proposed_sequence_number': self.sequence_id,
            'node_suggesting_sequence_id': self.sender_id,
            'status': 'undeliverable'
        })
        self.organize_holdback_queue()

    def send_proposed_priority(self, message: bytes):
        """send_proposed_priority should be called when a proposed_sequence should be send.

        TODO: This function should inside an if cause which checks if proposed sequence should be send.
        """
        message, address = self.receiver.receive()
        # message[1] is sequence_id of sender and address[0] is sender_id
        self.suggested_sequence_list.append((message[1], int(str(address[0]).split('.')[3])))
        
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
        self.sender.send_message_id_with_s_id_and_seq_id(message_id=message[0], sender_id=self.sender_id, sequence_id=max_sequence_number[0], 
                         senderid_from_sequence_id=max_sequence_number[1])
        # TODO: end if

    def send_final_sequence(self, message: bytes):
        """send_final_sequence_id should be called when the final proposed sequence should be re multicasted from the sender of the bid.

        TODO: This function should inside an if cause which checks for incoming messages in this format.
        """

        message, address = self.receiver.receive()
        # message[2] is the received sender_sequence
        self.sequence_id = max(self.sequence_id, message[2])
        for message_in_dict in self.holdback_queue:
            #message[0] is the received message_id and message[0] is the received sender_id
            if (message_in_dict['message_id'] == message[0]) and (message_in_dict['received_sender_IP'] == message[1]):
                # message[2] is the received sequence_id
                message_in_dict['proposed_sequence_number'] = message[2]
                # message[3] is the received sequence_id
                message_in_dict['node_suggesting_sequence_id'] = message[3]
                message_in_dict['status'] = 'deliverable'

        self.organize_holdback_queue()
