import os

from ipaddress import IPv4Address
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
    communication as com,
    TIMEOUT_RECEIVE,
    BUFFER_SIZE,
    MULTICAST_DISCOVERY_GROUP,
    MULTICAST_DISCOVERY_PORT,
    UNICAST_PORT,
)

from util import create_logger, logger


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
        super(AuctionManager, self).__init__()
        self._exit: Event = Event()

        self._name: str = f"AuctionManager::{auction.get_id()}::{os.getpid()}"
        self._logger: logger = create_logger(self._name.lower())

        self._auction: Auction = auction
        self._seen_mid: list[
            str
        ] = []  # List of seen message ids, to prevent duplicate responses

    def run(self) -> None:
        """Runs the auction manager process."""
        self._logger.info(f"{self._name} is starting background tasks")
        mc: Multicast = Multicast(
            group=MULTICAST_DISCOVERY_GROUP,
            port=MULTICAST_DISCOVERY_PORT,
            timeout=TIMEOUT_RECEIVE,
        )

        while not self._exit.is_set():
            # Receive request
            try:
                request, address = mc.receive(BUFFER_SIZE)
            except TimeoutError:
                continue

            if not MessageSchema.of(com.HEADER_AUCTION_INFORMATION_REQ, request):
                continue

            request: MessageAuctionInformationRequest = (
                MessageAuctionInformationRequest.decode(request)
            )

            if request._id in self._seen_mid:
                self._logger.info(
                    f"{self._name} received duplicate request {request} from {address}"
                )
                continue

            if not request.auction and self._auction.get_id() == request.auction:
                self._logger.info(
                    f"{self._name} received request {request} from {address} for another auction"
                )
                self._seen_mid.append(request._id)
                continue

            self._logger.info(f"{self._name} received request {request} from {address}")
            response: MessageAuctionInformationResponse = (
                MessageAuctionInformationResponse(
                    _id=request._id,
                    auction=AuctionMessageData.from_auction(self._auction),
                )
            )
            Unicast.qsend(
                message=response.encode(),
                host=IPv4Address(address[0]),
                port=request.port,
            )

        self._logger.info(f"{self._name} received stop signal; releasing resources")
        mc.close()

        self._logger.info(f"{self._name} stopped managing auction")

    def stop(self) -> None:
        """Stops the auction manager process."""
        self._logger.info(f"{self._name} received stop signal")
        self._exit.set()
