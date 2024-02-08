from __future__ import annotations

from dataclasses import dataclass, field
from marshmallow import validate
import marshmallow_dataclass

from constant import HEADER_ISIS_MESSAGE


@dataclass
class MessageIsisMessage:
    """Initial ISIS message.

    This message is used to send an initial ISIS message.

    Fields:
        _id: (str) Unique identifier of the message.
        header: (str) Header of the message. Should be constant HEADER_ISIS_MESSAGE.
        payload: (str) Payload of the message.
        reply_to: (tuple[str, int]) The address of the reliable unicast to reply to.
    """

    # Message ID
    _id: str = field(metadata={"validate": lambda x: len(x) > 0})
    header: str = field(
        default=HEADER_ISIS_MESSAGE,
        metadata={"validate": validate.OneOf([HEADER_ISIS_MESSAGE])},
    )

    # Message payload
    payload: str = field(
        default="",
        metadata={"validate": lambda x: isinstance(x, str) and len(x) > 0},
    )

    reply_to: tuple[str, int] = field(
        default=("", 0),
        metadata={"validate": lambda x: isinstance(x, tuple) and len(x) == 2},
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
        return self._id == o._id

    def encode(self) -> bytes:
        """Returns the encoded message."""
        return SCHEMA_MESSAGE_ISIS_MESSAGE().dumps(self).encode()

    @staticmethod
    def decode(message: bytes) -> MessageIsisMessage:
        """Return the decoded message."""
        return SCHEMA_MESSAGE_ISIS_MESSAGE().loads(message.decode())  # type: ignore


SCHEMA_MESSAGE_ISIS_MESSAGE = marshmallow_dataclass.class_schema(MessageIsisMessage)
