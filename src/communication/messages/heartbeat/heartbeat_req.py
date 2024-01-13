from __future__ import annotations

from dataclasses import dataclass, field
from marshmallow import validate
import marshmallow_dataclass

from json import dumps, loads

from constant import communication as com


@dataclass
class MessageHeartbeatRequest:
    """Request message for heartbeat.

    This message is sent as a unicast message to each replica in the pool to check if they are still alive.

    Fields:
        _id: (str) Unique identifier of the message. Structure is "uname::aname::uuid".
        header: (str) Header of the message. Should be constant HEADER_HEARTBEAT_REQ.
    """

    # Message ID
    _id: str = field(metadata={"validate": lambda x: len(x) > 0})
    header: str = field(
        default=com.HEADER_HEARTBEAT_REQ,
        metadata={"validate": validate.OneOf([com.HEADER_HEARTBEAT_REQ])},
    )

    def __str__(self) -> str:
        """Returns the string representation of the message."""
        return f"{com.HEADER_HEARTBEAT_REQ}(id={self._id})"

    def __repr__(self) -> str:
        """Returns the string representation of the message."""
        return self.__str__()

    def __eq__(self, o: object) -> bool:
        """Returns whether the value is equal to the message."""
        if not isinstance(o, MessageHeartbeatRequest):
            return False
        return self._id == o._id

    def encode(self) -> bytes:
        """Encodes the message into a bytes object."""
        return dumps(
            marshmallow_dataclass.class_schema(MessageHeartbeatRequest)().dump(self)
        ).encode()

    @staticmethod
    def decode(data: bytes) -> MessageHeartbeatRequest:
        """Decodes the bytes object into a message object."""
        return marshmallow_dataclass.class_schema(MessageHeartbeatRequest)().load(
            loads(data.decode())
        )
