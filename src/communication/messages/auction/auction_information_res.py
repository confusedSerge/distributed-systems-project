from typing import Self

from dataclasses import dataclass, field
from marshmallow import validate
import marshmallow_dataclass

from json import dumps, loads

from .auction_dataclass import AuctionData
from constant import communication as com


@dataclass
class MessageAuctionInformationResponse:
    """Response message for auction information."""

    _id: str = field(metadata={"validate": lambda x: not str(x)})
    header: str = field(
        default=com.HEADER_AUCTION_INFORMATION_RES,
        metadata={"validate": validate.OneOf([com.HEADER_AUCTION_INFORMATION_RES])},
    )

    # corresponding auction information.
    auction_information: AuctionData = field(
        default_factory=AuctionData,
        metadata={"validate": lambda x: isinstance(x, AuctionData)},
    )

    def __str__(self) -> str:
        """Returns the string representation of the message."""
        return f"{com.HEADER_AUCTION_INFORMATION_RES}(id={self._id}, auction_information={self.auction_information})"

    def __repr__(self) -> str:
        """Returns the string representation of the message."""
        return self.__str__()

    def __eq__(self, o: object) -> bool:
        """Returns whether the value is equal to the message."""
        if not isinstance(o, MessageAuctionInformationResponse):
            return False
        return self._id == o._id

    def encode(self) -> bytes:
        """Returns the encoded message."""
        return bytes(
            dumps(SCHEMA_MESSAGE_AUCTION_INFORMATION_RES().dump(self)), "utf-8"
        )

    @staticmethod
    def decode(message: bytes) -> Self:
        """Return the decoded auction information response."""
        return SCHEMA_MESSAGE_AUCTION_INFORMATION_RES().load(loads(message))


SCHEMA_MESSAGE_AUCTION_INFORMATION_RES = marshmallow_dataclass.class_schema(
    MessageAuctionInformationResponse
)
