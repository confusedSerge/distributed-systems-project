from typing import Self
from ipaddress import IPv4Address

from dataclasses import dataclass, field
from marshmallow import validate
import marshmallow_dataclass

from json import dumps, loads

from constant import communication as com


@dataclass
class MessageFindReplicaRequest:
    """Request message for finding replicas."""

    _id: str = field(metadata={"validate": lambda x: not str(x)})
    header: str = field(
        default=com.HEADER_FIND_REPLICA_REQ,
        metadata={"validate": validate.OneOf([com.HEADER_FIND_REPLICA_REQ])},
    )

    address: str = field(
        default="",
        metadata={
            "validate": lambda x: isinstance(x, str)
            and validate.Regexp(
                r"^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$", error="Invalid multicast address"
            )
        },
    )

    def __str__(self) -> str:
        """Returns the string representation of the message."""
        return f"{com.HEADER_FIND_REPLICA_REQ}(id={self._id}, address={self.address})"

    def __repr__(self) -> str:
        """Returns the string representation of the message."""
        return self.__str__()

    def __eq__(self, o: object) -> bool:
        """Returns whether the value is equal to the message."""
        if not isinstance(o, MessageFindReplicaRequest):
            return False
        return self._id == o._id

    def encode(self) -> bytes:
        """Returns the encoded message."""
        return bytes(dumps(SCHEMA_MESSAGE_FIND_REPLICA_REQUEST().dump(self)), "utf-8")

    @staticmethod
    def decode(message: bytes) -> Self:
        """Return the decoded find new replica request."""
        return SCHEMA_MESSAGE_FIND_REPLICA_REQUEST().load(loads(message))


SCHEMA_MESSAGE_FIND_REPLICA_REQUEST = marshmallow_dataclass.class_schema(
    MessageFindReplicaRequest
)
