from __future__ import annotations

from dataclasses import dataclass, field
from marshmallow import validate
import marshmallow_dataclass

from json import dumps, loads

from constant import HEADER_ISIS_MESSAGE


@dataclass
class MessageIsis:
    """Message to be B-multicasted to members of the group

    Fields:
        _id: (str) Unique identifier of the message. Structure is "uname::aname::uuid".
        header: (str) Header of the message. Should be constant HEADER_ISIS_MESSAGE.
        message_content: (str) content of the message.
        sender_ip: (int) the sender ip as id.
        
    """
    sendeissr_ip: int = field(
        metadata={
            "validate": lambda x: isinstance(x, int) and x > 0
        }
    )

    # Message ID
    _id: str = field(metadata={"validate": lambda x: len(x) > 0})
    
    # Data
    message_content: str = field(default="")
    header: str = field(
        default=HEADER_ISIS_MESSAGE,
        metadata={"validate": validate.OneOf([HEADER_ISIS_MESSAGE])},
    )

    def __str__(self) -> str:
        """Returns the string representation of the message."""
        return f"{HEADER_ISIS_MESSAGE}(id={self._id})"

    def __repr__(self) -> str:
        """Returns the string representation of the message."""
        return self.__str__()

    def __eq__(self, o: object) -> bool:
        """Returns whether the value is equal to the message."""
        if not isinstance(o, MessageIsis):
            return False
        return self._id == o._id

    def encode(self) -> bytes:
        """Encodes the message into a bytes object."""
        return dumps(
            marshmallow_dataclass.class_schema(MessageIsis)().dump(self)
        ).encode()

    @staticmethod
    def decode(data: bytes) -> MessageIsis:
        """Decodes the bytes object into a message object."""
        return marshmallow_dataclass.class_schema(MessageIsis)().load(
            loads(data.decode())
        )
