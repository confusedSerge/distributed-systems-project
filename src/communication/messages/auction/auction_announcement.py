from __future__ import annotations

from dataclasses import dataclass, field
from marshmallow import validate
import marshmallow_dataclass

from json import dumps, loads

from .auction_dataclass import AuctionData
from constant import HEADER_AUCTION_ANNOUNCEMENT


@dataclass
class MessageAuctionAnnouncement:
    """Announcement message for new auction.

    This message is sent by the auctioneer to the discovery multicast group to announce a new auction.

    Fields:
        _id: (str) Unique identifier of the message. Structure is "uname::aname::uuid".
        header: (str) Header of the message. Should be constant HEADER_AUCTION_ANNOUNCEMENT.
        auction: (AuctionData) Auction data.
    """

    # Message ID
    _id: str = field(metadata={"validate": lambda x: len(x) > 0})
    header: str = field(
        default=HEADER_AUCTION_ANNOUNCEMENT,
        metadata={"validate": validate.OneOf([HEADER_AUCTION_ANNOUNCEMENT])},
    )

    # Data
    auction: AuctionData = field(
        default_factory=AuctionData,  # type: ignore
        metadata={"validate": lambda x: isinstance(x, AuctionData)},
    )

    def __str__(self) -> str:
        """Returns the string representation of the message."""
        return f"{HEADER_AUCTION_ANNOUNCEMENT}(id={self._id}, auction={self.auction})"

    def __repr__(self) -> str:
        """Returns the string representation of the message."""
        return self.__str__()

    def __eq__(self, o: object) -> bool:
        """Returns whether the value is equal to the message."""
        if not isinstance(o, MessageAuctionAnnouncement):
            return False
        return self._id == o._id

    def encode(self) -> bytes:
        """Returns the encoded message."""
        return bytes(dumps(SCHEMA_MESSAGE_AUCTION_ANNOUNCEMENT().dump(self)), "utf-8")

    @staticmethod
    def decode(message: bytes) -> MessageAuctionAnnouncement:
        """Return the decoded auction announcement."""
        return SCHEMA_MESSAGE_AUCTION_ANNOUNCEMENT().load(
            loads(message.decode("utf-8"))
        )  # type: ignore


SCHEMA_MESSAGE_AUCTION_ANNOUNCEMENT = marshmallow_dataclass.class_schema(
    MessageAuctionAnnouncement
)
