from __future__ import annotations

from dataclasses import dataclass, field
from marshmallow import validate
import marshmallow_dataclass

from json import dumps, loads

from .auction_dataclass import AuctionData
from constant import HEADER_AUCTION_INFORMATION_REPLICATION


@dataclass
class MessageAuctionInformationReplication:
    """This message is used to replicate auction information to the other peers in the network.

    Fields:
        _id: (str) Unique identifier of the message. Structure is "uname::uuid". Corresponds to the request message ID.
        header: (str) Header of the message. Should be constant HEADER_AUCTION_INFORMATION_RES.
        auction: (AuctionData) Auction data corresponding to the auction ID in the request.
    """

    _id: str = field(metadata={"validate": lambda x: len(x) > 0})
    header: str = field(
        default=HEADER_AUCTION_INFORMATION_REPLICATION,
        metadata={"validate": validate.OneOf([HEADER_AUCTION_INFORMATION_REPLICATION])},
    )

    # corresponding auction information.
    auction: AuctionData = field(
        default_factory=AuctionData,  # type: ignore
        metadata={"validate": lambda x: isinstance(x, AuctionData)},
    )

    def __str__(self) -> str:
        """Returns the string representation of the message."""
        return f"{HEADER_AUCTION_INFORMATION_REPLICATION}(id={self._id}, auction={self.auction})"

    def __repr__(self) -> str:
        """Returns the string representation of the message."""
        return self.__str__()

    def __eq__(self, o: object) -> bool:
        """Returns whether the value is equal to the message."""
        if not isinstance(o, MessageAuctionInformationReplication):
            return False
        return self._id == o._id

    def encode(self) -> bytes:
        """Returns the encoded message."""
        return bytes(
            dumps(SCHEMA_MESSAGE_AUCTION_INFORMATION_RES().dump(self)), "utf-8"
        )

    @staticmethod
    def decode(message: bytes) -> MessageAuctionInformationReplication:
        """Return the decoded replica announcement."""
        return SCHEMA_MESSAGE_AUCTION_INFORMATION_RES().load(loads(message.decode("utf-8")))  # type: ignore


SCHEMA_MESSAGE_AUCTION_INFORMATION_RES = marshmallow_dataclass.class_schema(
    MessageAuctionInformationReplication
)
