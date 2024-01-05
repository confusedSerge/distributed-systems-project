from typing import Self

from dataclasses import dataclass, field
from marshmallow import Schema, fields, EXCLUDE
import marshmallow_dataclass

from json import dumps, loads

import constant.message


class MessageSchema(Schema):
    """MessageSchema class for marshmallow serialization."""

    tag = fields.String(required=True)
    _id = fields.Integer(required=True)

    class Meta:
        unknown = EXCLUDE


def decode(message: bytes) -> dict:
    """Return the decoded message

    Args:
        message (bytes): The message to decode.

    Returns:
        dict: The decoded message containing the tag and id.
    """
    return MessageSchema(partial=True).loads(message)


@dataclass
class FindReplicaRequest:
    """FindReplicaRequest class for sending and receiving find new replica requests."""

    tag: str = field(default=constant.message.FIND_REPLICA_REQUEST_TAG)
    _id: int = field(default=0)

    auction_multicast_group: str = field(default="")
    auction_multicast_port: int = field(default=0)

    def __str__(self) -> str:
        """Return the string representation of the find new replica request."""
        return f"FindNewReplicaRequest(tag={self.tag}, id={self._id}, auction_multicast={self.auction_multicast_group}:{self.auction_multicast_port})"

    def __repr__(self) -> str:
        """Return the string representation of the find new replica request."""
        return self.__str__()

    def __eq__(self, o: object) -> bool:
        """Return whether the find new replica request is equal to another find new replica request."""
        if not isinstance(o, FindReplicaRequest):
            return False
        return self._id == o._id and self.tag == o.tag

    def __hash__(self) -> int:
        """Return the hash of the find new replica request."""
        return hash(
            (
                self.tag,
                self._id,
                self.auction_multicast_group,
                self.auction_multicast_port,
            )
        )

    def encode(self) -> bytes:
        """Return the encoded find new replica request."""
        return bytes(dumps(FIND_REPLICA_REQUEST_SCHEMA().dump(self)), "utf-8")

    @staticmethod
    def decode(message: bytes) -> Self:
        """Return the decoded find new replica request."""
        return FIND_REPLICA_REQUEST_SCHEMA().load(loads(message))


FIND_REPLICA_REQUEST_SCHEMA = marshmallow_dataclass.class_schema(FindReplicaRequest)


@dataclass
class FindReplicaResponse:
    """FindReplicaResponse class for sending and receiving find new replica responses."""

    tag: str = field(default=constant.message.FIND_REPLICA_RESPONSE_TAG)
    _id: int = field(default=0)

    def __str__(self) -> str:
        """Return the string representation of the find new replica response."""
        return f"FindNewReplicaResponse(tag={self.tag}, id={self._id})"

    def __repr__(self) -> str:
        """Return the string representation of the find new replica response."""
        return self.__str__()

    def __eq__(self, o: object) -> bool:
        """Return whether the find new replica response is equal to another find new replica response."""
        if not isinstance(o, FindReplicaResponse):
            return False
        return self._id == o._id and self.tag == o.tag

    def __hash__(self) -> int:
        """Return the hash of the find new replica response."""
        return hash(
            (
                self.tag,
                self._id,
            )
        )

    def encode(self) -> bytes:
        """Return the encoded find new replica response."""
        return bytes(dumps(FIND_REPLICA_RESPONSE_SCHEMA().dump(self)), "utf-8")

    @staticmethod
    def decode(message: bytes) -> Self:
        """Return the decoded find new replica response."""
        return FIND_REPLICA_RESPONSE_SCHEMA().load(loads(message))


FIND_REPLICA_RESPONSE_SCHEMA = marshmallow_dataclass.class_schema(FindReplicaResponse)


@dataclass
class FindReplicaAcknowledge:
    """FindReplicaAcknowledge class for sending and receiving find new replica acknowledgements."""

    tag: str = field(default=constant.message.FIND_REPLICA_ACK_TAG)
    _id: int = field(default=0)

    def __str__(self) -> str:
        """Return the string representation of the find new replica acknowledgement."""
        return f"FindNewReplicaAcknowledge(tag={self.tag}, id={self._id})"

    def __repr__(self) -> str:
        """Return the string representation of the find new replica acknowledgement."""
        return self.__str__()

    def __eq__(self, o: object) -> bool:
        """Return whether the find new replica acknowledgement is equal to another find new replica acknowledgement."""
        if not isinstance(o, FindReplicaAcknowledge):
            return False
        return self._id == o._id and self.tag == o.tag

    def __hash__(self) -> int:
        """Return the hash of the find new replica acknowledgement."""
        return hash(
            (
                self.tag,
                self._id,
            )
        )

    def encode(self) -> bytes:
        """Return the encoded find new replica acknowledgement."""
        return bytes(dumps(FIND_REPLICA_ACKNOWLEDGE_SCHEMA().dump(self)), "utf-8")

    @staticmethod
    def decode(message: bytes) -> Self:
        """Return the decoded find new replica acknowledgement."""
        return FIND_REPLICA_ACKNOWLEDGE_SCHEMA().load(loads(message))


FIND_REPLICA_ACKNOWLEDGE_SCHEMA = marshmallow_dataclass.class_schema(
    FindReplicaAcknowledge
)


@dataclass
class AuctionReplicaPeers:
    """AuctionReplicaPeers class containing the peers of replicas for an auction."""

    tag: str = field(default=constant.message.AUCTION_REPLICA_PEERS_TAG)
    _id: int = field(default=0)

    peers: list[tuple[str, int]] = field(default_factory=list)

    def __str__(self) -> str:
        """Return the string representation of the replica peers."""
        return f"AuctionReplicaPeers(tag={self.tag}, id={self._id}, peers={self.peers})"

    def __repr__(self) -> str:
        """Return the string representation of the replica peers."""
        return self.__str__()

    def __eq__(self, o: object) -> bool:
        """Return whether the replica peers is equal to another replica peers."""
        if not isinstance(o, AuctionReplicaPeers):
            return False
        return self._id == o._id and self.tag == o.tag

    def __hash__(self) -> int:
        """Return the hash of the replica peers."""
        return hash(
            (
                self.tag,
                self._id,
                self.peers,
            )
        )

    def encode(self) -> bytes:
        """Return the encoded replica peers."""
        return bytes(dumps(AUCTION_REPLICA_PEERS_SCHEMA().dump(self)), "utf-8")

    @staticmethod
    def decode(message: bytes) -> Self:
        """Return the decoded replica peers."""
        return AUCTION_REPLICA_PEERS_SCHEMA().load(loads(message))


AUCTION_REPLICA_PEERS_SCHEMA = marshmallow_dataclass.class_schema(AuctionReplicaPeers)


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
        return self._id == o._id and self.tag == o.tag

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
