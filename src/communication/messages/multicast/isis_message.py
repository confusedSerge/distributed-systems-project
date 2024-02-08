from __future__ import annotations

from dataclasses import dataclass, field
from ipaddress import IPv4Network
from marshmallow import validate
import marshmallow_dataclass

from json import dumps, loads

from constant import HEADER_ISIS_MESSAGE


@dataclass
class MessageIsisMessage:
    """ISIS message to B-Multicast and find the counter of.

    Fields:
        _id: (str) Unique identifier of the message.
        header: (str) Header of the message. Should be constant HEADER_ISIS_MESSAGE.
        sender: (str) The sender of the message.
        b_sequence_number: (int) The sequence number of the message in the B-Multicast.
        payload: (str) Payload of the message.
    """

    # Message ID
    _id: str = field(metadata={"validate": lambda x: len(x) > 0})
    header: str = field(
        default=HEADER_ISIS_MESSAGE,
        metadata={"validate": validate.OneOf([HEADER_ISIS_MESSAGE])},
    )
    sender: str = field(
        default="",
        metadata={"validate": lambda x: isinstance(x, str) and len(x) > 0},
    )

    # Message payload
    b_sequence_number: int = field(default=0)
    payload: str = field(
        default="",
        metadata={"validate": lambda x: isinstance(x, str) and len(x) > 0},
    )

    def __str__(self) -> str:
        """Returns the string representation of the message."""
        return f"{HEADER_ISIS_MESSAGE}(id={self._id}, payload={self.payload})"

    def __repr__(self) -> str:
        """Returns the string representation of the message."""
        return self.__str__()

    def __eq__(self, o: object) -> bool:
        """Returns whether the value is equal to the message."""
        if not isinstance(o, MessageIsisMessage):
            return False
        return (
            self._id == o._id
            and self.b_sequence_number == o.b_sequence_number
            and self.sender == o.sender
        )

    def encode(self) -> bytes:
        """Encodes the message into a bytes object."""
        return SCHEMA_MESSAGE_ISIS_MESSAGE().dumps(self).encode()

    @staticmethod
    def decode(message: bytes) -> MessageIsisMessage:
        """Decodes the bytes object into a message object."""
        return SCHEMA_MESSAGE_ISIS_MESSAGE().loads(message.decode())  # type: ignore


SCHEMA_MESSAGE_ISIS_MESSAGE = marshmallow_dataclass.class_schema(MessageIsisMessage)
