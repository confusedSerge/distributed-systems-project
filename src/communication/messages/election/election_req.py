from dataclasses import dataclass, field
from marshmallow import validate
import marshmallow_dataclass

from json import dumps, loads
from constant import communication as com


@dataclass
class MessageElectionRequest:
    """Election request message.

    This message is used to initiate the leader election process.

    Fields:
        _id: (int) Unique identifier of the replicant.
        header: (str) Header of the message. Should be constant HEADER_ELECTION_REQ.
    """

    _id: int = field(
        metadata={
            "validate": lambda x: isinstance(x, int) and x > 0
        }
    )
    header: str = field(
        default=com.HEADER_ELECTION_REQ,
        metadata={"validate": validate.OneOf([com.HEADER_ELECTION_REQ])},
    )

    def __str__(self) -> str:
        """Returns the string representation of the message."""
        return f"{com.HEADER_ELECTION_REQ}(id={self._id})"

    def __repr__(self) -> str:
        """Returns the string representation of the message."""
        return self.__str__()

    def encode(self) -> bytes:
        """Returns the encoded message."""
        return bytes(
            dumps(SCHEMA_MESSAGE_ELECTION_REQ().dump(self)), "utf-8"
        )

    @staticmethod
    def decode(message: bytes) -> 'MessageElectionRequest':
        """Return the decoded election request."""
        return SCHEMA_MESSAGE_ELECTION_REQ().load(loads(message))


SCHEMA_MESSAGE_ELECTION_REQ = marshmallow_dataclass.class_schema(
    MessageElectionRequest
)