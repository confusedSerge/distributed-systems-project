from __future__ import annotations

from dataclasses import dataclass, field
from marshmallow import validate
import marshmallow_dataclass

from json import dumps, loads

from constant import HEADER_AUCTION_INFORMATION_ACK


@dataclass
class MessageAuctionInformationAcknowledgement:
    """Acknowledgement message for finding replicas.

    This message is sent over a udp unicast message to acknowledge a replica response, allowing the replica to join as such.

    Fields:
        _id: (str) Unique identifier of the message. Structure is "uname::aname::uuid". Corresponds to the request message ID.
        header: (str) Header of the message. Should be constant HEADER_FIND_REPLICA_ACK.
    """

    _id: str = field(metadata={"validate": lambda x: len(x) > 0})
    header: str = field(
        default=HEADER_AUCTION_INFORMATION_ACK,
        metadata={"validate": validate.OneOf([HEADER_AUCTION_INFORMATION_ACK])},
    )

    def __str__(self) -> str:
        """Returns the string representation of the message."""
        return f"{HEADER_AUCTION_INFORMATION_ACK}(id={self._id})"

    def __repr__(self) -> str:
        """Returns the string representation of the message."""
        return self.__str__()

    def __eq__(self, o: object) -> bool:
        """Returns whether the value is equal to the message."""
        if not isinstance(o, MessageAuctionInformationAcknowledgement):
            return False
        return self._id == o._id

    def encode(self) -> bytes:
        """Returns the encoded message."""
        return bytes(
            dumps(SCHEMA_MESSAGE_AUCTION_INFORMATION_ACK().dump(self)), "utf-8"
        )

    @staticmethod
    def decode(message: bytes) -> MessageAuctionInformationAcknowledgement:
        """Return the decoded find new replica ack."""
        return SCHEMA_MESSAGE_AUCTION_INFORMATION_ACK().load(
            loads(message.decode("utf-8"))
        )  # type: ignore


SCHEMA_MESSAGE_AUCTION_INFORMATION_ACK = marshmallow_dataclass.class_schema(
    MessageAuctionInformationAcknowledgement
)
