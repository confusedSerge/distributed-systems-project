from __future__ import annotations

from dataclasses import dataclass, field
from marshmallow import validate
import marshmallow_dataclass

from json import dumps, loads

from constant import HEADER_ELECTION_ALIVE


@dataclass
class MessageElectionImAlive:
    """Announcement message for reelection of leader in an auction

    Fields:
        _id: (int) Unique identifier of the replicant.
        header: (str) Header of the message. Should be constant HEADER_REELECTION_ANNOUNCEMENT.
    """

    _id: int = field(
        metadata={
            "validate": lambda x: isinstance(x, int) and x > 0
        }
    )
    header: str = field(
        default=HEADER_ELECTION_ALIVE,
        metadata={"validate": validate.OneOf([HEADER_ELECTION_ALIVE])},
    )

    def __str__(self) -> str:
        """Returns the string representation of the message."""
        return f"{HEADER_ELECTION_ALIVE}(id={self._id})"

    def __repr__(self) -> str:
        """Returns the string representation of the message."""
        return self.__str__()

    def __eq__(self, o: object) -> bool:
        """Returns whether the value is equal to the message."""
        if not isinstance(o, MessageElectionImAlive):
            return False
        return self._id == o._id

    def encode(self) -> bytes:
        """Encodes the message into a bytes object."""
        return dumps(
            marshmallow_dataclass.class_schema(MessageElectionImAlive)().dump(
                self
            )
        ).encode()

    @staticmethod
    def decode(data: bytes) -> MessageElectionImAlive:
        """Decodes the bytes object into a message object."""
        return marshmallow_dataclass.class_schema(MessageElectionImAlive)().load(
            loads(data.decode())
        )
