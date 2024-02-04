from __future__ import annotations

from dataclasses import dataclass, field
from marshmallow import validate
import marshmallow_dataclass

from json import dumps, loads

from constant import HEADER_AUCTION_STATE_ANNOUNCEMENT


@dataclass
class MessageAuctionStateAnnouncement:
    """Auction announcement announcing state changes of an auction.

    This message is sent by the auctioneer (replica leader) to the auction multicast group to announce state changes of an auction.

    Fields:
        _id: (str) Unique identifier of the message. Structure is "uname::aname::uuid".
        header: (str) Header of the message. Should be constant HEADER_AUCTION_STATE_ANNOUNCEMENT.
        state: (int) State of the auction.
    """

    # Data
    state: int = field(metadata={"validate": lambda x: isinstance(x, int)})

    # Message ID
    _id: str = field(metadata={"validate": lambda x: len(x) > 0})
    header: str = field(
        default=HEADER_AUCTION_STATE_ANNOUNCEMENT,
        metadata={"validate": validate.OneOf([HEADER_AUCTION_STATE_ANNOUNCEMENT])},
    )

    def __str__(self) -> str:
        """Returns the string representation of the message."""
        return f"{HEADER_AUCTION_STATE_ANNOUNCEMENT}(id={self._id}, state={self.state})"

    def __repr__(self) -> str:
        """Returns the string representation of the message."""
        return self.__str__()

    def __eq__(self, o: object) -> bool:
        """Returns whether the value is equal to the message."""
        if not isinstance(o, MessageAuctionStateAnnouncement):
            return False
        return self._id == o._id

    def encode(self) -> bytes:
        """Returns the encoded message."""
        return bytes(
            dumps(SCHEMA_MESSAGE_AUCTION_STATE_ANNOUNCEMENT().dump(self)), "utf-8"
        )

    @staticmethod
    def decode(message: bytes) -> MessageAuctionStateAnnouncement:
        """Return the decoded auction announcement."""
        return SCHEMA_MESSAGE_AUCTION_STATE_ANNOUNCEMENT().load(
            loads(message.decode("utf-8"))
        )  # type: ignore


SCHEMA_MESSAGE_AUCTION_STATE_ANNOUNCEMENT = marshmallow_dataclass.class_schema(
    MessageAuctionStateAnnouncement
)
