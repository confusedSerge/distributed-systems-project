from __future__ import annotations

from dataclasses import dataclass, field
from marshmallow import validate
import marshmallow_dataclass

from json import dumps, loads

from constant import communication as com


@dataclass
class MessageAgreedSequence:
    """the sender uses the proposed numbers to generate an agreed number

    Fields:
        _id: (str) Unique identifier of the message. Structure is "uname::aname::uuid".
        header: (str) Header of the message. Should be constant HEADER_AGREED_SEQ.
        sender_id: (int) sender id of the proposed sequence number , 
        sequence_id: (int) id of max sugessted sequence number, 
        senderid_from_sequence_id: (int) the sender id how sugessted the max sequence number
    """

    # Message ID
    _id: str = field(metadata={"validate": lambda x: len(x) > 0})
    header: str = field(
        default=com.HEADER_AGREED_SEQ,
        metadata={"validate": validate.OneOf([com.HEADER_AGREED_SEQ])},
    )

    # Data
    sender_id : int = field(default=0), 
    sequence_id : int = field(default=0), 
    senderid_from_sequence_id : int = field(default=0),

    def __str__(self) -> str:
        """Returns the string representation of the message."""
        return f"{com.HEADER_AGREED_SEQ}(id={self._id})"

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
