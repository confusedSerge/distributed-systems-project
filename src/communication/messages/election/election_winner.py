from __future__ import annotations

from dataclasses import dataclass, field
from marshmallow import validate
import marshmallow_dataclass

from json import dumps, loads

from constant import communication as com


@dataclass
class MessageElectionWin:
    """Announcement message for reelection of leader in an auction

    Fields:
        _id: (str) Unique identifier of the message. Structure is "uname::aname::uuid".
        header: (str) Header of the message. Should be constant HEADER_REELECTION_ANNOUNCEMENT.
    """

    # Message ID
    _id: str = field(metadata={"validate": lambda x: len(x) > 0})
    header: str = field(
        default=com.HEADER_ELECTION_WIN,
        metadata={"validate": validate.OneOf([com.HEADER_ELECTION_WIN])},
    )

    def __str__(self) -> str:
        """Returns the string representation of the message."""
        return f"{com.HEADER_ELECTION_WIN}(id={self._id})"

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
