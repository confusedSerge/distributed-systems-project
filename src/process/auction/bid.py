import os
from multiprocessing import Process, Event

from communication import Multicast, MessageSchema, MessageAuctionBid

from model import Auction
from constant import (
    communication as com,
    TIMEOUT_RECEIVE,
    BUFFER_SIZE,
    MULTICAST_AUCTION_PORT,
)

from util import create_logger, logger


class AuctionBidListener(Process):
    """Auction Bid listener process.

    This process listens to an auction bids and updates the auction state accordingly.
    """

    def __init__(self, auction: Auction):
        """Initializes the auction listener process.

        Args:
            auction (Auction): The auction to listen to. Should be a shared memory object.
        """
        super(AuctionBidListener, self).__init__()
        self._exit: Event = Event()

        self._name: str = f"AuctionListener::{auction.get_id()}::{os.getpid()}"
        self._logger: logger = create_logger(self._name.lower())

        self._auction: Auction = auction
        # List of seen message ids, to prevent duplicate bids
        self._seen_mid: list[str] = []

    def run(self) -> None:
        """Runs the auction listener process."""
        self._logger.info(f"{self._name} is starting background tasks")
        mc: Multicast = Multicast(
            group=self._auction.get_address(),
            port=MULTICAST_AUCTION_PORT,
            timeout=TIMEOUT_RECEIVE,
        )

        while self._auction.is_running() and not self._exit.is_set():
            # Receive bid
            try:
                bid, address = mc.receive(BUFFER_SIZE)
            except TimeoutError:
                continue

            if not MessageSchema.of(com.HEADER_AUCTION_BID, bid):
                continue

            bid: MessageAuctionBid = MessageAuctionBid.decode(bid)
            if bid._id in self._seen_mid:
                self._logger.info(
                    f"{self._name} received duplicate bid {bid} from {address}"
                )
                continue

            self._logger.info(f"{self._name} received bid {bid} from {address}")
            self._auction.add_bid(bid.bidder, bid.bid)
            self._seen_mid.append(bid._id)

        self._logger.info(f"{self._name} received stop signal; releasing resources")
        mc.close()

        self._logger.info(f"{self._name} stopped listening to auction")

    def stop(self) -> None:
        """Stops the auction listener process."""
        self._logger.info(f"{self._name} received stop signal")
        self._exit.set()
