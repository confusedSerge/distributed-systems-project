from typing import Self

from dataclasses import dataclass, field
from marshmallow import validate
import marshmallow_dataclass

from json import dumps, loads

from constant import communication as com


@dataclass
class MessageAuctionBid:
    """Message for auction bid.

    This message is sent by a bidder to the auction multicast group to place a bid.

    Fields:
        _id: (str) Unique identifier of the message. Structure is "uname::aname::uuid".
        header: (str) Header of the message. Should be constant HEADER_AUCTION_BID.
        bidder_id: (str) Bidders unique identifier (uname).
        bid: (float) Bid amount.
    """

    # Message ID
    _id: str = field(metadata={"validate": lambda x: len(x) > 0})
    header: str = field(
        default=com.HEADER_AUCTION_BID,
        metadata={"validate": validate.OneOf([com.HEADER_AUCTION_BID])},
    )

    # Data
    bidder: str = field(default="", metadata={"validate": lambda x: isinstance(x, str)})
    bid: float = field(
        default=0.0, metadata={"validate": lambda x: isinstance(x, float)}
    )

    def __str__(self) -> str:
        """Returns the string representation of the message."""
        return f"{com.HEADER_AUCTION_BID}(id={self._id}, bidder_id={self.bidder}, bid={self.bid})"

    def __repr__(self) -> str:
        """Returns the string representation of the message."""
        return self.__str__()

    def __eq__(self, o: object) -> bool:
        """Returns whether the value is equal to the message."""
        if not isinstance(o, MessageAuctionBid):
            return False
        return self._id == o._id

    def encode(self) -> bytes:
        """Returns the encoded message."""
        return bytes(dumps(SCHEMA_MESSAGE_AUCTION_BID().dump(self)), "utf-8")

    @staticmethod
    def decode(message: bytes) -> Self:
        """Return the decoded auction bid."""
        return SCHEMA_MESSAGE_AUCTION_BID().load(loads(message))


SCHEMA_MESSAGE_AUCTION_BID = marshmallow_dataclass.class_schema(MessageAuctionBid)
