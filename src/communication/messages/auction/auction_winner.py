from typing import Self

from dataclasses import dataclass, field
from marshmallow import validate
import marshmallow_dataclass

from json import dumps, loads

from constant import communication as com


@dataclass
class MessageAuctionWinner:
    """Message for auction winner notification."""

    _id: str = field(metadata={"validate": lambda x: not str(x)})
    header: str = field(
        default=com.HEADER_AUCTION_WIN,
        metadata={"validate": validate.OneOf([com.HEADER_AUCTION_WIN])},
    )

    auction_id: str = field(default="", metadata={"validate": lambda x: not str(x)})
    winner_id: str = field(default="", metadata={"validate": lambda x: not str(x)})
    winner_bid: float = field(
        default=0.0, metadata={"validate": lambda x: isinstance(x, float)}
    )

    def __str__(self) -> str:
        """Returns the string representation of the message."""
        return f"{com.HEADER_AUCTION_WIN}(id={self._id}, auction_id={self.auction_id}, winner_id={self.winner_id}, winner_bid={self.winner_bid})"

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
