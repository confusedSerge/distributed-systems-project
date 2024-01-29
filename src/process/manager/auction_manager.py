import os

from multiprocessing import Process, Event as ProcessEvent
from multiprocessing.synchronize import Event

from logging import Logger

# === Custom Modules ===

from communication import (
    Multicast,
    Unicast,
    MessageSchema,
    AuctionMessageData,
    MessageAuctionInformationRequest,
    MessageAuctionInformationResponse,
)
from model import Auction
from util import create_logger

from constant import (
    communication as com,
    TIMEOUT_RECEIVE,
    BUFFER_SIZE,
    MULTICAST_DISCOVERY_GROUP,
    MULTICAST_DISCOVERY_PORT,
)


class AuctionManager(Process):
    """Auction manager process for the leader replica.

    The auction manager is responsible for answering the following questions:
        - Auction Information Request: The auction manager answers to auction information requests.
    """

    def __init__(self, auction: Auction):
        """Initializes the auction manager process.

        Args:
            auction (Auction): The auction to manage. Should be a shared memory object.
        """
        super(AuctionManager, self).__init__()
        self._exit: Event = ProcessEvent()

        self._name: str = f"AuctionManager::{auction.get_id()}::{os.getpid()}"
        self._logger: Logger = create_logger(self._name.lower())

        self._auction: Auction = auction
        self._seen_message_id: list[str] = []

        self._logger.info(f"{self._name}: Initialized")

    def run(self) -> None:
        """Runs the auction manager process."""
        self._logger.info(f"{self._name}: Started")
        mc: Multicast = Multicast(
            group=MULTICAST_DISCOVERY_GROUP,
            port=MULTICAST_DISCOVERY_PORT,
            timeout=TIMEOUT_RECEIVE,
        )

        self._logger.info(f"{self._name}: Listening for auction information requests")
        while not self._exit.is_set():
            # Receive request
            try:
                message, address = mc.receive(BUFFER_SIZE)
            except TimeoutError:
                continue

            if (
                not MessageSchema.of(com.HEADER_AUCTION_INFORMATION_REQ, message)
                or MessageSchema.get_id(message) in self._seen_message_id
            ):
                continue

            request: MessageAuctionInformationRequest = (
                MessageAuctionInformationRequest.decode(message)
            )
            self._seen_message_id.append(request._id)

            if not request.auction and self._auction.get_id() == request.auction:
                self._logger.info(
                    f"{self._name}: Received request {request} from {address} for another auction"
                )
                continue

            self._logger.info(
                f"{self._name}: Received request {request} from {address} for {'all' if request.auction else 'auction ' + request.auction}"
            )
            response: MessageAuctionInformationResponse = (
                MessageAuctionInformationResponse(
                    _id=request._id,
                    auction=AuctionMessageData.from_auction(self._auction),
                )
            )
            Unicast.qsend(
                message=response.encode(),
                host=address[0],
                port=request.port,
            )
            self._logger.info(
                f"{self._name}: Sent response {response} to {address} for auction {self._auction.get_id()}"
            )

        self._logger.info(f"{self._name} received stop signal; releasing resources")
        mc.close()

        self._logger.info(f"{self._name} stopped managing auction")

    def stop(self) -> None:
        """Stops the auction manager process."""
        self._exit.set()
        self._logger.info(f"{self._name}: Stop signal received")
