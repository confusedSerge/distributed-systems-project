import os

from multiprocessing import Process, Event as ProcessEvent
from multiprocessing.synchronize import Event

from logging import Logger

# === Custom Modules ===

from communication import Multicast, MessageSchema, MessageAuctionBid

from model import Auction

from util import create_logger

from constant import (
    communication as com,
    TIMEOUT_RECEIVE,
    BUFFER_SIZE,
    MULTICAST_AUCTION_PORT,
)


class AuctionBidListener(Process):
    """Auction Bid listener process.

    This process listens to an auction bids and updates the auction bid history accordingly.
    """

    def __init__(self, auction: Auction):
        """Initializes the auction listener process.

        Args:
            auction (Auction): The auction to listen to. Should be a shared memory object.
        """
        super(AuctionBidListener, self).__init__()
        self._exit: Event = ProcessEvent()

        self._name: str = f"AuctionBidListener::{auction.get_id()}::{os.getpid()}"
        self._logger: Logger = create_logger(self._name.lower())

        self._auction: Auction = auction
        self._seen_message_id: list[str] = []

        self._logger.info(f"{self._name}: Initialized")

    def run(self) -> None:
        """Runs the auction listener process."""
        self._logger.info(f"{self._name}: Started")
        mc: Multicast = Multicast(
            group=self._auction.get_group(),
            port=MULTICAST_AUCTION_PORT,
            timeout=TIMEOUT_RECEIVE,
        )

        self._logger.info(f"{self._name}: Listening for bids on auction")
        while not self._exit.is_set():
            # Receive bid
            try:
                message, address = mc.receive(BUFFER_SIZE)
            except TimeoutError:
                continue

            if not MessageSchema.of(com.HEADER_AUCTION_BID, bid):
                continue

            bid: MessageAuctionBid = MessageAuctionBid.decode(bid)
            if bid._id in self._seen_message_id:
                self._logger.info(
                    f"{self._name}: Received duplicate bid {bid} from {address}"
                )
                continue

            try:
                if Auction.parse_id(bid._id) != self._auction.get_id():
                    self._logger.info(
                        f"{self._name}: Received bid {bid} from {address} for auction {Auction.parse_id(bid.auction)}"
                    )
                    continue
            except ValueError:
                self._logger.info(
                    f"{self._name}: Received bid {bid} with invalid auction id {bid._id}"
                )
                continue

            self._logger.info(
                f"{self._name}: Received bid {bid} from {address} for auction {self._auction.get_id()}"
            )

            self._auction.bid(bid.bidder, bid.bid)
            self._seen_message_id.append(bid._id)

        self._logger.info(f"{self._name}: Releasing resources")
        mc.close()

        self._logger.info(f"{self._name}: Stopped")

    def stop(self) -> None:
        """Stops the auction listener process."""
        self._exit.set()
        self._logger.info(f"{self._name}: Stopping")
