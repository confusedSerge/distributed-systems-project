from __future__ import annotations

from dataclasses import dataclass, field
from marshmallow import validate
import marshmallow_dataclass

from json import dumps, loads

from constant import HEADER_ELECTION_COORDINATOR


@dataclass
class MessageElectionCoordinator:
    """Election coordinator message.

    This message is used to coordinate the election process.

    Fields:
        _id: (str) Message ID.
        header: (str) Header of the message. Should be constant HEADER_ELECTION_COORDINATOR.
        req_id: (tuple[str, int]) The ID of the replica being elected.
    """

    # ID of the replica that is initiating the election.
    req_id: tuple[str, int] = field(
        metadata={"validate": lambda x: isinstance(x, tuple) and len(x) == 2}
    )

    # Message ID
    _id: str = field(metadata={"validate": lambda x: len(x) > 0})
    header: str = field(
        default=HEADER_ELECTION_COORDINATOR,
        metadata={"validate": validate.OneOf([HEADER_ELECTION_COORDINATOR])},
    )

    def __str__(self) -> str:
        """Returns the string representation of the message."""
        return f"{HEADER_ELECTION_COORDINATOR}(id={self._id})"

    def __repr__(self) -> str:
        """Returns the string representation of the message."""
        return self.__str__()

    def __eq__(self, o: object) -> bool:
        """Returns whether the value is equal to the message."""
        if not isinstance(o, MessageElectionCoordinator):
            return False
        return self._id == o._id

    def encode(self) -> bytes:
        """Encodes the message into a bytes object."""
        return bytes(dumps(SCHEMA_MESSAGE_ELECTION_COORDINATOR().dump(self)), "utf-8")

    @staticmethod
    def decode(data: bytes) -> MessageElectionCoordinator:
        """Decodes the bytes object into a message object."""
        return SCHEMA_MESSAGE_ELECTION_COORDINATOR().load(loads(data.decode("utf-8")))  # type: ignore


SCHEMA_MESSAGE_ELECTION_COORDINATOR = marshmallow_dataclass.class_schema(
    MessageElectionCoordinator
)
