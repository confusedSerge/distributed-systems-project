from typing import Self

from dataclasses import dataclass, field
from marshmallow import validate
import marshmallow_dataclass

from json import dumps, loads

from constant import communication as com


@dataclass
class MessageAuctionInformationRequest:
    """Request message for auction information.

    This message is sent over the discovery multicast group to request auction information, either for a specific auction or all auctions.
    The auction information is sent back over a udp unicast message.

    Fields:
        _id: (str) Unique identifier of the message. Structure is "uname::uuid".
        header: (str) Header of the message. Should be constant HEADER_AUCTION_INFORMATION_REQ.
        port: (int) Port to send the response to. (Host is the sender of the request)
        auction_id: (str) Auction ID of the auction to request information for. If empty str, return all auctions.
    """

    # Message ID
    _id: str = field(metadata={"validate": lambda x: len(x) > 0})
    header: str = field(
        default=com.HEADER_AUCTION_INFORMATION_REQ,
        metadata={"validate": validate.OneOf([com.HEADER_AUCTION_INFORMATION_REQ])},
    )

    # Response port
    port: int = field(
        default=com.UNICAST_PORT,
        metadata={
            "validate": lambda x: isinstance(x, int)
            and validate.Range(min=0, max=65535)
        },
    )

    # Data
    auction: str = field(
        default="",
        metadata={"validate": lambda x: isinstance(x, str)},
    )

    def __str__(self) -> str:
        """Returns the string representation of the message."""
        return f"{com.HEADER_AUCTION_INFORMATION_REQ}(id={self._id}, auction={self.auction})"

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
