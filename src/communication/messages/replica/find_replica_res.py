from typing import Self

from dataclasses import dataclass, field
from marshmallow import validate
import marshmallow_dataclass

from json import dumps, loads

from constant import communication as com


@dataclass
class MessageFindReplicaResponse:
    """Response message for finding replicas.

    This message is sent over a udp unicast message to respond to a find replica request.

    Fields:
        _id: (str) Unique identifier of the message. Structure is "uname::aname::uuid". Corresponds to the request message ID.
        header: (str) Header of the message. Should be constant HEADER_FIND_REPLICA_RES.
    """

    _id: str = field(metadata={"validate": lambda x: len(x) > 0})
    header: str = field(
        default=com.HEADER_FIND_REPLICA_RES,
        metadata={"validate": validate.OneOf([com.HEADER_FIND_REPLICA_RES])},
    )

    def __str__(self) -> str:
        """Returns the string representation of the message."""
        return f"{com.HEADER_FIND_REPLICA_RES}(id={self._id})"

    def __repr__(self) -> str:
        """Returns the string representation of the message."""
        return self.__str__()

    def __eq__(self, o: object) -> bool:
        """Returns whether the value is equal to the message."""
        if not isinstance(o, MessageFindReplicaResponse):
            return False
        return self._id == o._id

    def encode(self) -> bytes:
        """Returns the encoded message."""
        return bytes(dumps(SCHEMA_MESSAGE_FIND_REPLICA_RESPONSE().dump(self)), "utf-8")

    @staticmethod
    def decode(message: bytes) -> Self:
        """Return the decoded find new replica response."""
        return SCHEMA_MESSAGE_FIND_REPLICA_RESPONSE().load(loads(message))


SCHEMA_MESSAGE_FIND_REPLICA_RESPONSE = marshmallow_dataclass.class_schema(
    MessageFindReplicaResponse
)
