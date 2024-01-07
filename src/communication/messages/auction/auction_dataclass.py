from typing import Self

from dataclasses import dataclass, field
from marshmallow import validate
import marshmallow_dataclass

from json import dumps, loads

from model import Auction


@dataclass
class AuctionData:
    """Auction data class for representing an auction and sending it over the network."""

    # TODO: Add all the other fields.
    _id: str = field(metadata={"validate": validate.Validator(lambda x: not str(x))})

    # Basic auction information.
    item: str = field(
        metadata={"validate": validate.Validator(lambda x: isinstance(x, str))}
    )
    price: int = field(
        metadata={"validate": validate.Validator(lambda x: isinstance(x, int))}
    )
    time: int = field(
        metadata={"validate": validate.Validator(lambda x: isinstance(x, int))}
    )

    # Multicast address for the auction.
    multicast_address: tuple[str, int] = field(
        metadata={
            "validate": validate.Validator(
                lambda x: len(x) == 2
                and isinstance(x[0], str)
                and isinstance(x[1], int)
            )
        }
    )

    def __str__(self) -> str:
        """Return the string representation of the auction data."""
        return f"AuctionData(id={self._id}, item={self.item}, price={self.price}, time={self.time}, multicast_address={self.multicast_address})"

    def __repr__(self) -> str:
        """Return the string representation of the auction data."""
        return self.__str__()

    def __eq__(self, o: object) -> bool:
        """Return whether the auction data is equal to another auction data."""
        if not isinstance(o, AuctionData):
            return False
        return self._id == o._id

    def encode(self) -> bytes:
        """Return the encoded auction data."""
        return bytes(dumps(AUCTION_DATA_SCHEMA().dump(self)), "utf-8")

    @staticmethod
    def decode(message: bytes) -> Self:
        """Return the decoded auction data."""
        return AUCTION_DATA_SCHEMA().load(loads(message))

    def to_auction(self) -> Auction:
        """Return the auction from the auction data."""
        return Auction(
            _id=self._id,
            item=self.item,
            price=self.price,
            time=self.time,
            multicast_address=self.multicast_address,
        )

    @staticmethod
    def from_auction(auction: Auction) -> Self:
        """Return the auction data from the auction."""
        return AuctionData(
            _id=auction.get_id(),
            item=auction.get_item(),
            price=auction.get_price(),
            time=auction.get_time(),
            multicast_address=auction.get_multicast_address(),
        )


AUCTION_DATA_SCHEMA = marshmallow_dataclass.class_schema(AuctionData)
