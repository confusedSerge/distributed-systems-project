from multiprocessing import Process, Event

from communication import (
    Multicast,
    Unicast,
    MessageSchema,
    AuctionMessageData,
    MessageAuctionInformationRequest,
    MessageAuctionInformationResponse,
)

from model import Auction
from constant import (
    header as hdr,
    MULTICAST_DISCOVERY_GROUP,
    MULTICAST_DISCOVERY_PORT,
    UNICAST_PORT,
)

from util import create_logger


class AuctionManager(Process):
    """Auction manager process.

    The auction manager is responsible for answering the following questions:
    - Auction Information Request: The auction manager answers to auction information requests, where the requested id corresponds to an auction managed by this auction manager.
    """

    def __init__(self, auction: Auction):
        """Initializes the auction manager process.

        Args:
            auction (Auction): The auction to manage. Should be a shared memory object.
        """
        super().__init__()
        self._exit = Event()

        self._auction: Auction = auction

        self.name = f"AuctionManager-{auction.get_id()}"
        self.logger = create_logger(self.name.lower())

    def run(self) -> None:
        """Runs the auction manager process."""
        self.logger.info(f"{self.name} is starting background tasks")
        mc = Multicast(MULTICAST_DISCOVERY_GROUP, MULTICAST_DISCOVERY_PORT)

        while not self._exit.is_set():
            # Receive request
            request, address = mc.receive()

            if not MessageSchema.of(hdr.AUCTION_INFORMATION_REQUEST, request):
                continue

            request: MessageAuctionInformationRequest = (
                MessageAuctionInformationRequest.decode(request)
            )
            if not request.auction_id and self._auction.get_id() == request.auction_id:
                self.logger.info(
                    f"{self.name} received request {request} from {address} for another auction"
                )
                continue

            self.logger.info(f"{self.name} received request {request} from {address}")
            Unicast.qsend(
                MessageAuctionInformationResponse(
                    self._auction.get_id(),
                    auction_information=AuctionMessageData.from_auction(self._auction),
                ),
                address,
                UNICAST_PORT,
            )

        self.logger.info(f"{self.name} stopped managing auction")

    def stop(self) -> None:
        """Stops the auction manager process."""
        self.logger.info(f"{self.name} received stop signal")
        self._exit.set()
