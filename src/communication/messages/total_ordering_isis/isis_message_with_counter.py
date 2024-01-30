from __future__ import annotations

from dataclasses import dataclass, field
from ipaddress import IPv4Network
from marshmallow import validate
import marshmallow_dataclass

from json import dumps, loads

from constant import HEADER_ISIS_MESSAGE_WITH_COUNTER


@dataclass
class MessageIsisWithCounter:
    """Message to be B-multicasted to members of the group

    Fields:
        counter: (int) Unique identifier of the message. In this case it is a counter since every new message id is incremented by 1.
        header: (str) Header of the message. Should be constant HEADER_ISIS_MESSAGE.
        sender_id: (int) the sender id.
        
    """

    # Data
    counter: int = field(
        metadata={
            "validate": lambda x: isinstance(x, int) and x > 0
        }
    )
    message_content: str
    header: str = field(
        default=HEADER_ISIS_MESSAGE_WITH_COUNTER,
        metadata={"validate": validate.OneOf([HEADER_ISIS_MESSAGE_WITH_COUNTER])},
    )

    def __str__(self) -> str:
        """Returns the string representation of the message."""
        return f"{HEADER_ISIS_MESSAGE_WITH_COUNTER}(id={self.message_content}, counter={self.counter})"

    def __repr__(self) -> str:
        """Returns the string representation of the message."""
        return self.__str__()

    def __eq__(self, o: object) -> bool:
        """Returns whether the value is equal to the message."""
        if not isinstance(o, MessageIsisWithCounter):
            return False
        return self._id == o._id

    def encode(self) -> bytes:
        """Encodes the message into a bytes object."""
        return dumps(
            marshmallow_dataclass.class_schema(MessageIsisWithCounter)().dump(self)
        ).encode()

    @staticmethod
    def decode(data: bytes) -> MessageIsisWithCounter:
        """Decodes the bytes object into a message object."""
        return marshmallow_dataclass.class_schema(MessageIsisWithCounter)().load(
            loads(data.decode())
        )
