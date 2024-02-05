from __future__ import annotations

from dataclasses import dataclass, field
from marshmallow import validate
import marshmallow_dataclass

from json import dumps, loads

from constant import HEADER_RELIABLE_REQ


@dataclass
class MessageReliableRequest:
    """Reliable request message.

    This message is used to send a reliable request.
    This should be used in conjunction with the reliable response message as the ack for the request.

    Fields:
        _id: (str) Unique identifier of the message.
        header: (str) Header of the message. Should be constant HEADER_RELIABLE_REQ.
        checksum: (str) Checksum of the message.
        payload: (str) Payload of the message.
    """

    # Message ID
    _id: str = field(metadata={"validate": lambda x: len(x) > 0})
    header: str = field(
        default=HEADER_RELIABLE_REQ,
        metadata={"validate": validate.OneOf([HEADER_RELIABLE_REQ])},
    )

    # Message checksum
    checksum: str = field(
        default="",
        metadata={"validate": lambda x: isinstance(x, str) and len(x) > 0},
    )

    # Message payload
    payload: str = field(
        default="",
        metadata={"validate": lambda x: isinstance(x, str) and len(x) > 0},
    )

    def __str__(self) -> str:
        """Returns the string representation of the message."""
        return f"{HEADER_RELIABLE_REQ}(id={self._id}, payload={self.payload})"

    def __repr__(self) -> str:
        """Returns the string representation of the message."""
        return self.__str__()

    def __eq__(self, o: object) -> bool:
        """Returns whether the value is equal to the message."""
        if not isinstance(o, MessageReliableRequest):
            return False
        return self._id == o._id

    def encode(self) -> bytes:
        """Returns the encoded message."""
        return SCHEMA_MESSAGE_RELIABLE_REQUEST().dumps(self).encode()

    @staticmethod
    def decode(message: bytes) -> MessageReliableRequest:
        """Return the decoded find new replica ack."""
        return SCHEMA_MESSAGE_RELIABLE_REQUEST().loads(message.decode())  # type: ignore


SCHEMA_MESSAGE_RELIABLE_REQUEST = marshmallow_dataclass.class_schema(
    MessageReliableRequest
)
