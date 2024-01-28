from __future__ import annotations

from dataclasses import dataclass, field
import socket
from marshmallow import validate
import marshmallow_dataclass

from json import dumps, loads

from constant import communication as com

@dataclass
class MessageElectionResponse:
    """Election response message.

    This message is used to respond to an election request.

    Fields:
        _id: (int) Unique identifier of the replicant. Should match the ID of the election request.
        header: (str) Header of the message. Should be constant HEADER_ELECTION_RES.
    """

    _id: int = field(
        metadata={
            "validate": lambda x: isinstance(x, int) and x > 0
        }
    )
    header: str = field(
        default=com.HEADER_ELECTION_RES,
        metadata={"validate": validate.OneOf([com.HEADER_ELECTION_RES])},
    )

    def __str__(self) -> str:
        """Returns the string representation of the message."""
        return f"{com.HEADER_ELECTION_RES}(id={self._id}"

    def __repr__(self) -> str:
        """Returns the string representation of the message."""
        return self.__str__()

    def encode(self) -> bytes:
        """Returns the encoded message."""
        return bytes(
            dumps(SCHEMA_MESSAGE_ELECTION_RES().dump(self)), "utf-8"
        )

    @staticmethod
    def decode(message: bytes) -> 'MessageElectionResponse':
        """Return the decoded election response."""
        return SCHEMA_MESSAGE_ELECTION_RES().load(loads(message))


SCHEMA_MESSAGE_ELECTION_RES = marshmallow_dataclass.class_schema(
    MessageElectionResponse
)