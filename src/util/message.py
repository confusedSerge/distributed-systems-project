from typing import Self

from dataclasses import dataclass, field
import marshmallow_dataclass

from json import dumps, loads

import constant.message


@dataclass
class FindReplicaRequest:
    """FindReplicaRequest class for sending and receiving find new replica requests."""

    tag: str = field(default=constant.message.FIND_REPLICA_REQUEST_TAG)
    _id: int = field(default=0)
    data: str = field(default="")

    def __str__(self) -> str:
        """Return the string representation of the find new replica request."""
        return f"FindNewReplicaRequest(tag={self.tag}, data={self.data})"

    def __repr__(self) -> str:
        """Return the string representation of the find new replica request."""
        return self.__str__()

    def __eq__(self, o: object) -> bool:
        """Return whether the find new replica request is equal to another find new replica request."""
        if not isinstance(o, FindReplicaRequest):
            return False
        return self.__hash__() == o.__hash__()

    def __hash__(self) -> int:
        """Return the hash of the find new replica request."""
        return hash((self.tag, self.data))

    def encode(self) -> bytes:
        """Return the encoded find new replica request."""
        return bytes(dumps(FIND_REPLICA_REQUEST_SCHEMA().dump(self)), "utf-8")

    @staticmethod
    def decode(message: bytes) -> Self:
        """Return the decoded find new replica request."""
        return FIND_REPLICA_REQUEST_SCHEMA().load(loads(message))


FIND_REPLICA_REQUEST_SCHEMA = marshmallow_dataclass.class_schema(FindReplicaRequest)


@dataclass
class AuctionAnnouncement:
    """AuctionAnnouncement class for sending and receiving auction announcements.

    This includes the item, price, time and multicast group of the auction.
    """

    tag: str = field(default=constant.message.AUCTION_ANNOUNCEMENT_TAG)
    _id: int = field(default=0)
    item: str = field(default="")
    price: float = field(default=0.0)
    time: int = field(default=0)

    multicast_group: str = field(default="")
    multicast_port: int = field(default=0)

    def __str__(self) -> str:
        """Return the string representation of the auction announcement."""
        return f"AuctionAnnouncement(tag={self.tag}, item={self.item}, price={self.price}, time={self.time}, multicast={self.multicast_group}:{self.multicast_port})"

    def __repr__(self) -> str:
        """Return the string representation of the auction announcement."""
        return self.__str__()

    def __eq__(self, o: object) -> bool:
        """Return whether the auction announcement is equal to another auction announcement."""
        if not isinstance(o, AuctionAnnouncement):
            return False
        return self._id == o._id

    def __hash__(self) -> int:
        """Return the hash of the auction announcement."""
        return hash(
            (
                self.tag,
                self._id,
                self.item,
                self.price,
                self.time,
                self.multicast_group,
                self.multicast_port,
            )
        )

    def encode(self) -> bytes:
        """Return the encoded auction announcement."""
        return bytes(dumps(AUCTION_ANNOUNCEMENT_SCHEMA().dump(self)), "utf-8")

    @staticmethod
    def decode(message: bytes) -> Self:
        """Return the decoded auction announcement."""
        return AUCTION_ANNOUNCEMENT_SCHEMA().load(loads(message))


AUCTION_ANNOUNCEMENT_SCHEMA = marshmallow_dataclass.class_schema(AuctionAnnouncement)
