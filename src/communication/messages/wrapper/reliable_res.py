from __future__ import annotations

from dataclasses import dataclass, field
from marshmallow import validate
import marshmallow_dataclass

from json import dumps, loads

from constant import HEADER_RELIABLE_RES


@dataclass
class MessageReliableResponse:
    """Reliable response message.

    This message is used to send a reliable response.
    This should be used in conjunction with the reliable request message as the ack for the request.

    Fields:
        _id: (str) Unique identifier of the message. Corresponds to the request message ID.
        header: (str) Header of the message. Should be constant HEADER_RELIABLE_RES.
    """

    # Message ID
    _id: str = field(metadata={"validate": lambda x: len(x) > 0})
    header: str = field(
        default=HEADER_RELIABLE_RES,
        metadata={"validate": validate.OneOf([HEADER_RELIABLE_RES])},
    )

    def __str__(self) -> str:
        """Returns the string representation of the message."""
        return f"{HEADER_RELIABLE_RES}(id={self._id})"

    def __repr__(self) -> str:
        """Returns the string representation of the message."""
        return self.__str__()

    def __eq__(self, o: object) -> bool:
        """Returns whether the value is equal to the message."""
        if not isinstance(o, MessageReliableResponse):
            return False
        return self._id == o._id

    def encode(self) -> bytes:
        """Returns the encoded message."""
        return bytes(dumps(SCHEMA_MESSAGE_RELIABLE_RES().dump(self)), "utf-8")

    @staticmethod
    def decode(message: bytes) -> MessageReliableResponse:
        """Return the decoded reliable response."""
        return SCHEMA_MESSAGE_RELIABLE_RES().load(loads(message.decode("utf-8")))  # type: ignore


SCHEMA_MESSAGE_RELIABLE_RES = marshmallow_dataclass.class_schema(
    MessageReliableResponse
)
