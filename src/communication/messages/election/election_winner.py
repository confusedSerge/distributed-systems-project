from __future__ import annotations

from dataclasses import dataclass, field
from marshmallow import validate
import marshmallow_dataclass

from json import dumps, loads

from constant import HEADER_ELECTION_WIN


@dataclass
class MessageElectionWin:
    """Announcement message for reelection of leader in an auction

    Fields:
        _id: (int) Unique identifier of the replicant.
        header: (str) Header of the message. Should be constant HEADER_REELECTION_WIN.
    """

    # Message ID
    _id: int = field(
        metadata={
            "validate": lambda x: isinstance(x, int) and x > 0
        }
    )
    header: str = field(
        default=HEADER_ELECTION_WIN,
        metadata={"validate": validate.OneOf([HEADER_ELECTION_WIN])},
    )

    def __str__(self) -> str:
        """Returns the string representation of the message."""
        return f"{HEADER_ELECTION_WIN}(id={self._id})"

    def __repr__(self) -> str:
        """Returns the string representation of the message."""
        return self.__str__()

    def __eq__(self, o: object) -> bool:
        """Returns whether the value is equal to the message."""
        if not isinstance(o, MessageElectionWin):
            return False
        return self._id == o._id

    def encode(self) -> bytes:
        """Encodes the message into a bytes object."""
        return dumps(
            marshmallow_dataclass.class_schema(MessageElectionWin)().dump(
                self
            )
        ).encode()

    @staticmethod
    def decode(data: bytes) -> MessageElectionWin:
        """Decodes the bytes object into a message object."""
        return marshmallow_dataclass.class_schema(MessageElectionWin)().load(
            loads(data.decode())
        )
