from __future__ import annotations

from dataclasses import dataclass, field
from marshmallow import validate
import marshmallow_dataclass

from json import dumps, loads

from constant import HEADER_FIND_REPLICA_REQ


@dataclass
class MessageFindReplicaRequest:
    """Request message for finding replicas.

    This message is sent over the discovery multicast group to request for new replicas.

    Fields:
        _id: (str) Unique identifier of the message. Structure is "uname::aname::uuid".
        header: (str) Header of the message. Should be constant HEADER_FIND_REPLICA_REQ.
        port: (int) Port to send the response to. (Host is the sender of the request)
        address: (str) Address of the multicast group for the auction.
    """

    # Message ID
    _id: str = field(metadata={"validate": lambda x: len(x) > 0})
    header: str = field(
        default=HEADER_FIND_REPLICA_REQ,
        metadata={"validate": validate.OneOf([HEADER_FIND_REPLICA_REQ])},
    )

    # Response port
    port: int = field(
        default=0,
        metadata={
            "validate": lambda x: isinstance(x, int)
            and validate.Range(min=0, max=65535)
        },
    )

    # Auction address
    address: str = field(
        default="",
        metadata={
            "validate": lambda x: isinstance(x, str)
            and validate.Regexp(
                r"^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$", error="Invalid address"
            )
        },
    )

    def __str__(self) -> str:
        """Returns the string representation of the message."""
        return f"{HEADER_FIND_REPLICA_REQ}(id={self._id}, address={self.address})"

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
    def decode(message: bytes) -> MessageFindReplicaRequest:
        """Return the decoded find new replica request."""
        return SCHEMA_MESSAGE_FIND_REPLICA_REQUEST().load(loads(message.decode("utf-8")))  # type: ignore


SCHEMA_MESSAGE_FIND_REPLICA_REQUEST = marshmallow_dataclass.class_schema(
    MessageFindReplicaRequest
)
