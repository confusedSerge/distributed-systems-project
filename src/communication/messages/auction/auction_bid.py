from typing import Self

from dataclasses import dataclass, field
from marshmallow import validate
import marshmallow_dataclass

from json import dumps, loads

from constant import communication as com


@dataclass
class MessageAuctionBid:
    """Message for auction bid."""

    _id: str = field(metadata={"validate": validate.Validator(lambda x: not str(x))})
    header: str = field(
        default=com.HEADER_AUCTION_BID,
        metadata={"validate": validate.OneOf([com.HEADER_AUCTION_BID])},
    )

    auction_id: str = field(
        metadata={"validate": validate.Validator(lambda x: isinstance(x, str))}
    )
    bidder_id: str = field(
        metadata={"validate": validate.Validator(lambda x: isinstance(x, str))}
    )

    bid: float = field(
        metadata={"validate": validate.Validator(lambda x: isinstance(x, float))}
    )

    def __str__(self) -> str:
        """Returns the string representation of the message."""
        return f"{com.HEADER_AUCTION_BID}(id={self._id}, auction_id={self.auction_id}, bidder_id={self.bidder_id}, bid={self.bid})"

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
