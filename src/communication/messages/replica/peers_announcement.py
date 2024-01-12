from typing import Self, List

from dataclasses import dataclass, field
from marshmallow import validate
import marshmallow_dataclass

from json import dumps, loads

from constant import communication as com


@dataclass
class MessagePeersAnnouncement:
    """Announcement message for new replicas.

    This message is sent by the auctioneer to all replicas to announce their respective peers in the auction.

    Fields:
        _id: (str) Unique identifier of the message. Structure is "uname::aname::uuid".
        header: (str) Header of the message. Should be constant HEADER_REPLICA_ANNOUNCEMENT.
        replicas: (List[str]) List of replica addresses.
    """

    # Message ID
    _id: str = field(metadata={"validate": lambda x: len(x) > 0})
    header: str = field(
        default=com.HEADER_PEERS_ANNOUNCEMENT,
        metadata={"validate": validate.OneOf([com.HEADER_PEERS_ANNOUNCEMENT])},
    )

    # Data
    peers: List[str] = field(
        default_factory=list,
        metadata={"validate": lambda x: isinstance(x, list)},
    )

    def __str__(self) -> str:
        """Returns the string representation of the message."""
        return f"{com.HEADER_PEERS_ANNOUNCEMENT}(id={self._id}, replicas={self.peers})"

    def __repr__(self) -> str:
        """Returns the string representation of the message."""
        return self.__str__()

    def __eq__(self, o: object) -> bool:
        """Returns whether the value is equal to the message."""
        if not isinstance(o, MessagePeersAnnouncement):
            return False
        return self._id == o._id

    def encode(self) -> bytes:
        """Returns the encoded message."""
        return bytes(dumps(SCHEMA_MESSAGE_REPLICA_ANNOUNCEMENT().dump(self)), "utf-8")

    @staticmethod
    def decode(message: bytes) -> Self:
        """Return the decoded replica announcement."""
        return SCHEMA_MESSAGE_REPLICA_ANNOUNCEMENT().load(
            loads(message.decode("utf-8"))
        )


SCHEMA_MESSAGE_REPLICA_ANNOUNCEMENT = marshmallow_dataclass.class_schema(
    MessagePeersAnnouncement
)