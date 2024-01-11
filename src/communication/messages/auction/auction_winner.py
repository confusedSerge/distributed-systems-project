from typing import Self

from dataclasses import dataclass, field
from marshmallow import validate
import marshmallow_dataclass

from json import dumps, loads

from constant import communication as com


@dataclass
class MessageAuctionWinner:
    """Message for auction winner notification.

    This message is sent by all replicas to the auction multicast group to notify the winner of an auction.

    Fields:
        _id: (str) Unique identifier of the message. Structure is "uname::aname::uuid".
        header: (str) Header of the message. Should be constant HEADER_AUCTION_WIN.
        auction: (str) Auction ID of the auction that was won. Structure is "uname::aname".
        winner: (str) Winner of the auction. Username of the winner.
        bid: (float) Winning bid amount.
    """

    _id: str = field(metadata={"validate": lambda x: not str(x)})
    header: str = field(
        default=com.HEADER_AUCTION_WIN,
        metadata={"validate": validate.OneOf([com.HEADER_AUCTION_WIN])},
    )

    auction: str = field(default="", metadata={"validate": lambda x: not str(x)})
    winner: str = field(default="", metadata={"validate": lambda x: not str(x)})
    bid: float = field(
        default=0.0, metadata={"validate": lambda x: isinstance(x, float)}
    )

    def __str__(self) -> str:
        """Returns the string representation of the message."""
        return f"{com.HEADER_AUCTION_WIN}(id={self._id}, auction={self.auction}, winner={self.winner}, bid={self.bid})"

    def __repr__(self) -> str:
        """Returns the string representation of the message."""
        return self.__str__()

    def __eq__(self, o: object) -> bool:
        """Returns whether the value is equal to the message."""
        if not isinstance(o, MessageAuctionWinner):
            return False
        return self._id == o._id

    def encode(self) -> bytes:
        """Returns the encoded message."""
        return bytes(dumps(SCHEMA_MESSAGE_AUCTION_WINNER().dump(self)), "utf-8")

    @staticmethod
    def decode(message: bytes) -> Self:
        """Return the decoded auction winner."""
        return SCHEMA_MESSAGE_AUCTION_WINNER().load(loads(message))


SCHEMA_MESSAGE_AUCTION_WINNER = marshmallow_dataclass.class_schema(MessageAuctionWinner)
