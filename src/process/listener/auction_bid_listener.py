from multiprocessing import Process, Event as ProcessEvent
from multiprocessing.synchronize import Event

from logging import Logger

# === Custom Modules ===

from communication import Multicast, MessageSchema, MessageAuctionBid
from model import Auction
from util import create_logger

from constant import (
    communication as com,
    COMMUNICATION_BUFFER_SIZE,
    COMMUNICATION_TIMEOUT,
    MULTICAST_AUCTION_BID_PORT,
)


class AuctionBidListener(Process):
    """Auction Bid listener process.

    This process listens to an auction bids and updates the auction bid history accordingly.

    # TODO: USE ISIS ALGORITHM TO ORDER THE BIDS FOR REPLICAS, no need when it is a bidder listening to the auction.
    """

    def __init__(self, auction: Auction):
        """Initializes the auction listener process.

        Args:
            auction (Auction): The auction to listen to. Should be a shared memory object.
        """
        super(AuctionBidListener, self).__init__()
        self._exit: Event = ProcessEvent()

        self._name: str = self.__class__.__name__.lower()
        self._prefix: str = f"{self._name}::{auction.get_id()}"
        self._logger: Logger = create_logger(self._name, with_pid=True)

        self._auction: Auction = auction
        self._seen_message_id: list[str] = []

    def run(self) -> None:
        """Runs the auction listener process."""
        self._logger.info(f"{self._prefix}: Initialized for {self._auction.get_id()}")

        self._logger.info(f"{self._prefix}: Started")
        mc: Multicast = Multicast(
            group=self._auction.get_group(),
            port=MULTICAST_AUCTION_BID_PORT,
            timeout=COMMUNICATION_TIMEOUT,
        )

        self._logger.info(f"{self._prefix}: Listening for bids on auction")
        while not self._exit.is_set():
            # Receive bid
            try:
                message, address = mc.receive(COMMUNICATION_BUFFER_SIZE)
            except TimeoutError:
                continue

            if (
                not MessageSchema.of(com.HEADER_AUCTION_BID, message)
                or MessageSchema.get_id(message) in self._seen_message_id
            ):
                continue

            bid: MessageAuctionBid = MessageAuctionBid.decode(message)

            try:
                parsed_id = Auction.parse_id(bid._id)
            except ValueError:
                self._logger.info(
                    f"{self._prefix}: Received bid: ith invalid auction id: {bid}"
                )
                continue

            if parsed_id != self._auction.get_id():
                self._logger.info(
                    f"{self._prefix}: Ignoring received bid from {address} for different auction {parsed_id} (expected {self._auction.get_id()}): {bid}"
                )
                continue

            self._logger.info(f"{self._prefix}: Received bid from {address}: {bid}")

            self._seen_message_id.append(bid._id)
            self._auction.bid(bid.bidder, bid.bid)

            self._logger.info(
                f"{self._prefix}: Updated auction state with bid from {address}: {bid}"
            )

        self._logger.info(f"{self._prefix}: Releasing resources")
        mc.close()

        self._logger.info(f"{self._prefix}: Stopped")

    def stop(self) -> None:
        """Stops the auction listener process."""
        self._exit.set()
        self._logger.info(f"{self._prefix}: Stopping")
