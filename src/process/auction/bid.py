import os
from multiprocessing import Process, Event

from communication import Multicast, MessageSchema, MessageAuctionBid

from model import Auction
from constant import auction as state, header as hdr, TIMEOUT_RECEIVE

from util import create_logger


class AuctionBidListener(Process):
    """Auction Bid listener process.

    This process listens to an auction bids and updates the auction state accordingly.
    """

    def __init__(self, auction: Auction):
        """Initializes the auction listener process.

        Args:
            auction (Auction): The auction to listen to. Should be a shared memory object.
        """
        super().__init__()
        self._exit = Event()

        self._name = f"AuctionListener-{auction.get_id()}-{os.getpid()}"
        self._logger = create_logger(self._name.lower())

        self._auction: Auction = auction

    def run(self) -> None:
        """Runs the auction listener process."""
        self._logger.info(f"{self._name} is starting background tasks")
        mc = Multicast(*self._auction.get_multicast_address(), timeout=TIMEOUT_RECEIVE)

        while (
            self._auction.get_state() != state.AUCTION_ENDED and not self._exit.is_set()
        ):
            # Receive bid
            try:
                bid, address = mc.receive()
            except TimeoutError:
                continue

            if not MessageSchema.of(hdr.AUCTION_BID, bid):
                continue

            bid: MessageAuctionBid = MessageAuctionBid.decode(bid)
            if bid.auction_id != self._auction.get_id():
                self._logger.info(
                    f"{self._name} received bid {bid} from {address} for another auction"
                )
                continue

            self._logger.info(f"{self._name} received bid {bid} from {address}")
            self._auction.add_bid(bid.bidder_id, bid.bid)

        self._logger.info(f"{self._name} received stop signal; releasing resources")
        mc.close()

        self._logger.info(f"{self._name} stopped listening to auction")

    def stop(self) -> None:
        """Stops the auction listener process."""
        self._logger.info(f"{self._name} received stop signal")
        self._exit.set()
