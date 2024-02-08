from __future__ import annotations

from dataclasses import dataclass, field
from marshmallow import validate
import marshmallow_dataclass

from json import dumps, loads

from constant import HEADER_ISIS_MESSAGE_AGREED_SEQ


@dataclass
class MessageIsisAgreedSequence:
    """the sender uses the proposed numbers to generate an agreed number

    Fields:
        _id: (str) Unique identifier of the message. Should be the same as the corresponding message.
        header: (str) Header of the message. Should be constant HEADER_ISIS_MESSAGE_AGREED_SEQ.
        agreed_sequence: (int) The agreed sequence_id of the sender.
    """

    # Message ID
    _id: str = field(metadata={"validate": lambda x: len(x) > 0})
    header: str = field(
        default=HEADER_ISIS_MESSAGE_AGREED_SEQ,
        metadata={"validate": validate.OneOf([HEADER_ISIS_MESSAGE_AGREED_SEQ])},
    )

    # Data
    agreed_sequence: int = field(default=0)

    def __str__(self) -> str:
        """Returns the string representation of the message."""
        return f"{HEADER_ISIS_MESSAGE_AGREED_SEQ}(id={self._id}, agreed_sequence={self.agreed_sequence})"

    def __repr__(self) -> str:
        """Returns the string representation of the message."""
        return self.__str__()

    def __eq__(self, o: object) -> bool:
        """Returns whether the value is equal to the message."""
        if not isinstance(o, MessageIsisAgreedSequence):
            return False
        return self._id == o._id

    def encode(self) -> bytes:
        """Returns the encoded message."""
        return SCHEMA_MESSAGE_ISIS_AGREED_SEQ().dumps(self).encode()

    @staticmethod
    def decode(message: bytes) -> MessageIsisAgreedSequence:
        """Return the decoded find new replica ack."""
        return SCHEMA_MESSAGE_ISIS_AGREED_SEQ().loads(message.decode())  # type: ignore


SCHEMA_MESSAGE_ISIS_AGREED_SEQ = marshmallow_dataclass.class_schema(
    MessageIsisAgreedSequence
)
