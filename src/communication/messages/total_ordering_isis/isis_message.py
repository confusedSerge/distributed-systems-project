from __future__ import annotations

from dataclasses import dataclass, field
from marshmallow import validate
import marshmallow_dataclass

from json import dumps, loads

from constant import communication as com


@dataclass
class MessageIsis:
    """Message to be B-multicasted to members of the group

    Fields:
        _id: (str) Unique identifier of the message. Structure is "uname::aname::uuid".
        header: (str) Header of the message. Should be constant HEADER_ISIS_MESSAGE.
        message_content: (str) content of the message.
        sender_ip: (int) the sender ip as id.
        
    """

    # Message ID
    _id: str = field(metadata={"validate": lambda x: len(x) > 0})
    header: str = field(
        default=com.HEADER_ISIS_MESSAGE,
        metadata={"validate": validate.OneOf([com.HEADER_ISIS_MESSAGE])},
    )

    # Data
    message_content: str = field(default="")
    sendeissr_ip: int = field(default=0)

    def __str__(self) -> str:
        """Returns the string representation of the message."""
        return f"{com.HEADER_ISIS_MESSAGE}(id={self._id})"

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
