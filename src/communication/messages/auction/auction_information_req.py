from typing import Self

from dataclasses import dataclass, field
from marshmallow import validate
import marshmallow_dataclass

from json import dumps, loads

from constant import communication as com


@dataclass
class MessageAuctionInformationRequest:
    """Request message for auction information."""

    _id: str = field(metadata={"validate": validate.Validator(lambda x: not str(x))})
    header: str = field(
        default=com.HEADER_AUCTION_INFORMATION_REQ,
        metadata={"validate": validate.OneOf([com.HEADER_AUCTION_INFORMATION_REQ])},
    )

    # corresponding auction information. If empty str, return all auctions.
    auction_id: str = field(
        default="",
        metadata={"validate": validate.Validator(lambda x: isinstance(x, str))},
    )

    def __str__(self) -> str:
        """Returns the string representation of the message."""
        return f"{com.HEADER_AUCTION_INFORMATION_REQ}(id={self._id}, auction_id={self.auction_id})"

    def __repr__(self) -> str:
        """Returns the string representation of the message."""
        return self.__str__()

    def __eq__(self, o: object) -> bool:
        """Returns whether the value is equal to the message."""
        if not isinstance(o, MessageAuctionInformationRequest):
            return False
        return self._id == o._id

    def encode(self) -> bytes:
        """Returns the encoded message."""
        return bytes(
            dumps(SCHEMA_MESSAGE_AUCTION_INFORMATION_REQ().dump(self)), "utf-8"
        )

    @staticmethod
    def decode(message: bytes) -> Self:
        """Return the decoded auction information request."""
        return SCHEMA_MESSAGE_AUCTION_INFORMATION_REQ().load(loads(message))


SCHEMA_MESSAGE_AUCTION_INFORMATION_REQ = marshmallow_dataclass.class_schema(
    MessageAuctionInformationRequest
)
