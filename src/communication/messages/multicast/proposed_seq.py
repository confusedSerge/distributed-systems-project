from __future__ import annotations

from dataclasses import dataclass, field
from marshmallow import validate
import marshmallow_dataclass

from json import dumps, loads

from constant import HEADER_ISIS_MESSAGE_PROPOSED_SEQ


@dataclass
class MessageIsisProposedSequence:
    """ISIS message containing a proposed sequence_id for the corresponding message

    Fields:
        _id: (str) Unique identifier of the message. Should be the same as the corresponding message.
        header: (str) Header of the message. Should be constant HEADER_PROPOSED_SEQ.
        proposed_sequence: (int) The proposed sequence_id of the sender.
    """

    # Message ID
    _id: str = field(metadata={"validate": lambda x: len(x) > 0})
    header: str = field(
        default=HEADER_ISIS_MESSAGE_PROPOSED_SEQ,
        metadata={"validate": validate.OneOf([HEADER_ISIS_MESSAGE_PROPOSED_SEQ])},
    )

    # Data
    proposed_sequence: int = field(default=0)

    def __str__(self) -> str:
        """Returns the string representation of the message."""
        return f"{HEADER_ISIS_MESSAGE_PROPOSED_SEQ}(id={self._id}, proposed_sequence={self.proposed_sequence})"

    def __repr__(self) -> str:
        """Returns the string representation of the message."""
        return self.__str__()

    def __eq__(self, o: object) -> bool:
        """Returns whether the value is equal to the message."""
        if not isinstance(o, MessageIsisProposedSequence):
            return False
        return self._id == o._id

    def encode(self) -> bytes:
        """Encodes the message into a bytes object."""
        return SCHEMA_MESSAGE_ISIS_PROPOSED_SEQ().dumps(self).encode()

    @staticmethod
    def decode(message: bytes) -> MessageIsisProposedSequence:
        """Decodes the bytes object into a message object."""
        return SCHEMA_MESSAGE_ISIS_PROPOSED_SEQ().loads(message.decode())  # type: ignore


SCHEMA_MESSAGE_ISIS_PROPOSED_SEQ = marshmallow_dataclass.class_schema(
    MessageIsisProposedSequence
)
