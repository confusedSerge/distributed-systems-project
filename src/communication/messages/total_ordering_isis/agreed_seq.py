from __future__ import annotations

from dataclasses import dataclass, field
from marshmallow import validate
import marshmallow_dataclass

from json import dumps, loads

from constant import HEADER_AGREED_SEQ


@dataclass
class MessageAgreedSequence:
    """the sender uses the proposed numbers to generate an agreed number

    Fields:
        message_id: (int) Unique identifier of the message.
        header: (str) Header of the message. Should be constant HEADER_AGREED_SEQ.
        sender_id: (int) sender id of the proposed sequence number , 
        sequence_id: (int) id of max sugessted sequence number, 
        senderid_from_sequence_id: (int) the sender id how sugessted the max sequence number
    """

    # Message ID
    message_id: int = field(
        metadata={
            "validate": lambda x: isinstance(x, int) and x > 0
        }
    )
    header: str = field(
        default=HEADER_AGREED_SEQ,
        metadata={"validate": validate.OneOf([HEADER_AGREED_SEQ])},
    )

    # Data
    sender_id : int = field(
        metadata={
            "validate": lambda x: isinstance(x, int) and x > 0
        }
    ) 
    sequence_id : int = field(
        metadata={
            "validate": lambda x: isinstance(x, int) and x > 0
        }
    )
    sender_id_from_sequence_id : int = field(
        metadata={
            "validate": lambda x: isinstance(x, int) and x > 0
        }
    )

    def __str__(self) -> str:
        """Returns the string representation of the message."""
        return f"{HEADER_AGREED_SEQ}(message_id={self.message_id}, sender_id={self.sender_id}, sequence_id={self.sequence_id}, sender_id_from_seuquence_id={self.sender_id_from_sequence_id})"

    def __repr__(self) -> str:
        """Returns the string representation of the message."""
        return self.__str__()

    def __eq__(self, o: object) -> bool:
        """Returns whether the value is equal to the message."""
        if not isinstance(o, MessageAgreedSequence):
            return False
        return self._id == o._id

    def encode(self) -> bytes:
        """Encodes the message into a bytes object."""
        return dumps(
            marshmallow_dataclass.class_schema(MessageAgreedSequence)().dump(self)
        ).encode()

    @staticmethod
    def decode(data: bytes) -> MessageAgreedSequence:
        """Decodes the bytes object into a message object."""
        return marshmallow_dataclass.class_schema(MessageAgreedSequence)().load(
            loads(data.decode())
        )
