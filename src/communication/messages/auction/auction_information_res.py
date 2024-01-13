from typing import Self

from dataclasses import dataclass, field
from marshmallow import validate
import marshmallow_dataclass

from json import dumps, loads

from .auction_dataclass import AuctionData
from constant import communication as com


@dataclass
class MessageAuctionInformationResponse:
    """Response message for auction information request.

    This message is sent over a udp unicast message to respond to a auction information request.
    The _id field is the same as the request message.

    Fields:
        _id: (str) Unique identifier of the message. Structure is "uname::uuid". Corresponds to the request message ID.
        header: (str) Header of the message. Should be constant HEADER_AUCTION_INFORMATION_RES.
        port: (int) Port to send the response to. (Host is the sender of the request)
        auction: (AuctionData) Auction data corresponding to the auction ID in the request.
    """

    _id: str = field(metadata={"validate": lambda x: len(x) > 0})
    header: str = field(
        default=com.HEADER_AUCTION_INFORMATION_RES,
        metadata={"validate": validate.OneOf([com.HEADER_AUCTION_INFORMATION_RES])},
    )

    # Acknowledgement UC port
    port: int = field(
        default=com.UNICAST_PORT,
        metadata={
            "validate": lambda x: isinstance(x, int)
            and validate.Range(min=0, max=65535)
        },
    )

    # corresponding auction information.
    auction: AuctionData = field(
        default_factory=AuctionData,
        metadata={"validate": lambda x: isinstance(x, AuctionData)},
    )

    def __str__(self) -> str:
        """Returns the string representation of the message."""
        return f"{com.HEADER_AUCTION_INFORMATION_RES}(id={self._id}, auction={self.auction})"

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
