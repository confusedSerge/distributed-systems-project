from typing import Self

from dataclasses import dataclass, field
from marshmallow import validate
import marshmallow_dataclass

from json import dumps, loads

from constant import communication as com


@dataclass
class MessageFindReplicaResponse:
    """Response message for finding replicas."""

    _id: str = field(metadata={"validate": validate.Validator(lambda x: not str(x))})
    header: str = field(
        default=com.HEADER_FIND_REPLICA_RESPONSE,
        metadata={"validate": validate.OneOf([com.HEADER_FIND_REPLICA_RESPONSE])},
    )

    def __str__(self) -> str:
        """Returns the string representation of the message."""
        return f"{com.HEADER_FIND_REPLICA_RESPONSE}(id={self._id})"

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
