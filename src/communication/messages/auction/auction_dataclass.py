from __future__ import annotations

from ipaddress import IPv4Address

from dataclasses import dataclass, field
from marshmallow import validate
import marshmallow_dataclass

from json import dumps, loads

from model import Auction


@dataclass
class AuctionData:
    """Auction data class for representing an auction and sending it over the network.

    Fields:
        _id: (str) Unique identifier of the auction. Structure is "uname::aname".
        name: (str) Name of the auction. Also referred to as aname.
        auctioneer: (str) Auctioneer of the auction. Here uname.

        item: (str) Item being auctioned.
        price: (int) Starting price of the auction.
        time: (float) Time for the auction.

        multicast_address: (str) Multicast address for the auction.

        state: (int) State of the auction.
        bid_history: (list[tuple[str, int]]) Bid history of the auction.
    """

    # Auction ID, name and auctioneer
    _id: str = field(metadata={"validate": lambda x: len(x) > 0})
    name: str = field(metadata={"validate": lambda x: isinstance(x, str)})
    auctioneer: str = field(metadata={"validate": lambda x: isinstance(x, str)})

    # Auction information
    item: str = field(metadata={"validate": lambda x: isinstance(x, str)})
    price: float = field(metadata={"validate": lambda x: isinstance(x, float)})
    time: float = field(metadata={"validate": lambda x: isinstance(x, float)})

    # Multicast address for the auction
    group: str = field(
        metadata={
            "validate": lambda x: isinstance(x, str)
            and validate.Regexp(
                r"^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$", error="Invalid multicast address"
            )
        }
    )

    # Auction state
    state: int = field(metadata={"validate": lambda x: isinstance(x, int)})
    bid_history: list[tuple[str, float]] = field(
        metadata={
            "validate": lambda x: isinstance(x, list)
            and all(
                isinstance(y, tuple)
                and len(y) == 2
                and isinstance(y[0], str)
                and isinstance(y[1], float)
                for y in x
            )
        }
    )

    def __str__(self) -> str:
        """Return the string representation of the auction data."""
        return f"AuctionData(id={self._id}, item={self.item}, price={self.price}, time={self.time}, address={self.group}, state={self.state}, bid_history={self.bid_history})"

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
    def decode(message: bytes) -> AuctionData:
        """Return the decoded auction data."""
        return AUCTION_DATA_SCHEMA().load(loads(message.decode("utf-8")))  # type: ignore

    def to_auction(self) -> Auction:
        """Return the auction from the auction data."""
        auction: Auction = Auction(
            name=self.name,
            auctioneer=self.auctioneer,
            item=self.item,
            price=self.price,
            time=self.time,
            group=IPv4Address(self.group),
        )
        auction._set_id(self._id)
        auction.set_state(self.state)
        auction._set_bid_history(self.bid_history)
        return auction

    @staticmethod
    def from_auction(auction: Auction) -> AuctionData:
        """Return the auction data from the auction."""
        return AuctionData(
            _id=auction.get_id(),
            name=auction.get_name(),
            auctioneer=auction.get_auctioneer(),
            item=auction.get_item(),
            price=auction.get_price(),
            time=auction.get_end_time(),
            group=str(auction.get_group()),
            state=auction.get_state()[0],
            bid_history=auction.get_bid_history(),
        )


AUCTION_DATA_SCHEMA = marshmallow_dataclass.class_schema(AuctionData)
