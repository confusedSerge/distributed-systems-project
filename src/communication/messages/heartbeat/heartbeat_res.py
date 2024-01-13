from __future__ import annotations

from dataclasses import dataclass, field
from marshmallow import validate
import marshmallow_dataclass

from json import dumps, loads

from constant import communication as com


@dataclass
class MessageHeartbeatResponse:
    """Response message for heartbeat.

    This message is sent as a unicast message to the sender of the heartbeat request to notify that the replica is still alive.
    The id of the heartbeat response should be the same as the id of the heartbeat request.

    Fields:
        _id: (str) Unique identifier of the message. Structure is "uname::aname::uuid".
        header: (str) Header of the message. Should be constant HEADER_HEARTBEAT_RES.
    """

    # Message ID
    _id: str = field(metadata={"validate": lambda x: len(x) > 0})
    header: str = field(
        default=com.HEADER_HEARTBEAT_RES,
        metadata={"validate": validate.OneOf([com.HEADER_HEARTBEAT_RES])},
    )

    def __str__(self) -> str:
        """Returns the string representation of the message."""
        return f"{com.HEADER_HEARTBEAT_RES}(id={self._id})"

    def __repr__(self) -> str:
        """Returns the string representation of the message."""
        return self.__str__()

    def __eq__(self, o: object) -> bool:
        """Returns whether the value is equal to the message."""
        if not isinstance(o, MessageHeartbeatResponse):
            return False
        return self._id == o._id

    def encode(self) -> bytes:
        """Encodes the message into a bytes object."""
        return dumps(
            marshmallow_dataclass.class_schema(MessageHeartbeatResponse)().dump(self)
        ).encode()

    @staticmethod
    def decode(data: bytes) -> MessageHeartbeatResponse:
        """Decodes the bytes object into a message object."""
        return marshmallow_dataclass.class_schema(MessageHeartbeatResponse)().load(
            loads(data.decode())
        )
