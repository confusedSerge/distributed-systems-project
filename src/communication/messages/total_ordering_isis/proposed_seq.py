from __future__ import annotations

from dataclasses import dataclass, field
from marshmallow import validate
import marshmallow_dataclass

from json import dumps, loads

from constant import HEADER_PROPOSED_SEQ


@dataclass
class MessageProposedSequence:
    """the receiving processes propose numbers and return them to the sender

    Fields:
        header: (str) Header of the message. Should be constant HEADER_PROPOSED_SEQ.
        proposed_sequence: (int) The proposed sequence_id of the sender.
    """

    # Message ID
    header: str = field(
        default=HEADER_PROPOSED_SEQ,
        metadata={"validate": validate.OneOf([HEADER_PROPOSED_SEQ])},
    )

    # Data
    proposed_sequence: int = field(default=0)

    def __str__(self) -> str:
        """Returns the string representation of the message."""
        return f"{HEADER_PROPOSED_SEQ}(proposed_sequence={self.proposed_sequence})"

    def __repr__(self) -> str:
        """Returns the string representation of the message."""
        return self.__str__()

    def __eq__(self, o: object) -> bool:
        """Returns whether the value is equal to the message."""
        if not isinstance(o, MessageProposedSequence):
            return False
        return self._id == o._id

    def encode(self) -> bytes:
        """Encodes the message into a bytes object."""
        return dumps(
            marshmallow_dataclass.class_schema(MessageProposedSequence)().dump(self)
        ).encode()

    @staticmethod
    def decode(data: bytes) -> MessageProposedSequence:
        """Decodes the bytes object into a message object."""
        return marshmallow_dataclass.class_schema(MessageProposedSequence)().load(
            loads(data.decode())
        )