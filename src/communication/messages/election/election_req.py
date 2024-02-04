from __future__ import annotations

from dataclasses import dataclass, field
from marshmallow import validate
import marshmallow_dataclass

from json import dumps, loads
from constant import HEADER_ELECTION_REQ


@dataclass
class MessageElectionRequest:
    """Election request message.

    This message is used to initiate the leader election process.

    Fields:
        _id: (str): Message ID.
        header: (str) Header of the message. Should be constant HEADER_ELECTION_REQ.
        req_id: (tuple[str, int]) The ID of the replica that is initiating the election.
    """

    # ID of the replica that is initiating the election.
    req_id: tuple[str, int] = field(
        metadata={"validate": lambda x: isinstance(x, tuple) and len(x) == 2}
    )

    _id: str = field(metadata={"validate": lambda x: len(x) > 0})
    header: str = field(
        default=HEADER_ELECTION_REQ,
        metadata={"validate": validate.OneOf([HEADER_ELECTION_REQ])},
    )

    def __str__(self) -> str:
        """Returns the string representation of the message."""
        return f"{HEADER_ELECTION_REQ}(id={self._id})"

    def __repr__(self) -> str:
        """Returns the string representation of the message."""
        return self.__str__()

    def encode(self) -> bytes:
        """Returns the encoded message."""
        return bytes(dumps(SCHEMA_MESSAGE_ELECTION_REQ().dump(self)), "utf-8")

    @staticmethod
    def decode(message: bytes) -> MessageElectionRequest:
        """Return the decoded election request."""
        return SCHEMA_MESSAGE_ELECTION_REQ().load(loads(message.decode("utf-8")))  # type: ignore


SCHEMA_MESSAGE_ELECTION_REQ = marshmallow_dataclass.class_schema(MessageElectionRequest)
