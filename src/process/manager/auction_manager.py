import os

from multiprocessing import Process, Event as ProcessEvent
from multiprocessing.synchronize import Event

from logging import Logger
from time import time

# === Custom Modules ===

from communication import (
    Multicast,
    Unicast,
    MessageSchema,
    AuctionMessageData,
    MessageAuctionInformationRequest,
    MessageAuctionInformationResponse,
)
from communication import MessageAuctionAnnouncement, MessageAuctionStateAnnouncement
from model import Auction
from util import create_logger, generate_message_id

from constant import (
    communication as com,
    TIMEOUT_RECEIVE,
    BUFFER_SIZE,
    MULTICAST_DISCOVERY_GROUP,
    MULTICAST_DISCOVERY_PORT,
    MULTICAST_AUCTION_PORT,
    MULTICAST_AUCTION_ANNOUNCEMENT_PERIOD,
)


class AuctionManager(Process):
    """Auction manager process for the leader replica.

    The auction manager is responsible for answering the following questions:
        - Auction Preparation: The auction manager prepares the auction for running.
        - Auction Information Request: The auction manager answers to auction information requests.
        - Auction State Announcement: The auction manager announces state changes of the auction.
        - Auction Announcement: The auction manager periodically announces the auction to the discovery multicast group (if the auction is still running).

    The auction manager finalizes the auction by moving it to the final state, when the time is up.
    If the auction is in the state preparing, the auction manager will move the auction to the state running.
    """

    def __init__(self, auction: Auction):
        """Initializes the auction manager process.

        Args:
            auction (Auction): The auction to manage. Should be a shared memory object.
        """
        super(AuctionManager, self).__init__()
        self._exit: Event = ProcessEvent()

        self._name: str = self.__class__.__name__.lower()
        self._prefix: str = f"{self._name}::{auction.get_id()}"
        self._logger: Logger = create_logger(self._name, with_pid=True)

        self._auction: Auction = auction
        self._last_auction_state: tuple[int, str] = self._auction.get_state()
        self._last_auction_announcement: float = 0.0

        self._seen_message_id: list[str] = []

        self._logger.info(f"{self._prefix}: Initialized")

    def run(self) -> None:
        """Runs the auction manager process."""
        mc_discovery_receiver: Multicast = Multicast(
            group=MULTICAST_DISCOVERY_GROUP,
            port=MULTICAST_DISCOVERY_PORT,
            timeout=TIMEOUT_RECEIVE,
        )

        mc_discovery_sender: Multicast = Multicast(
            group=MULTICAST_DISCOVERY_GROUP,
            port=MULTICAST_DISCOVERY_PORT,
            sender=True,
        )

        mc_auction_sender: Multicast = Multicast(
            group=self._auction.get_group(),
            port=MULTICAST_AUCTION_PORT,
            sender=True,
        )

        if self._auction.is_preparation():
            self._initial_auction_prep(mc_discovery_sender)

        self._logger.info(f"{self._prefix}: Started")
        self._logger.info(f"{self._prefix}: Listening for auction information requests")
        while not self._exit.is_set():
            self._auction_state_changes()
            self._auction_announcement(mc_discovery_sender)
            self._auction_state_announcement(mc_auction_sender)
            self._auction_information_request(mc_discovery_receiver)

        self._logger.info(f"{self._prefix} received stop signal; releasing resources")
        mc_discovery_sender.close()

        self._logger.info(f"{self._prefix} stopped managing auction")

    def stop(self) -> None:
        """Stops the auction manager process."""
        self._exit.set()
        self._logger.info(f"{self._prefix}: Stop signal received")

    # === Helper ===

    def _initial_auction_prep(self, mc_discovery: Multicast) -> None:
        """Prepares the auction for running.

        If the auction is in the state preparing, the auction manager will move the auction to the state running.
        Announces the running auction to the discovery multicast group.

        Args:
            mc_discovery (Multicast): The multicast object to use for sending the auction information response.
        """
        assert self._auction.is_preparation(), "Auction is not in preparation state"
        self._logger.info(
            f"{self._prefix}: Auction is in preparation state; moving to running state"
        )
        self._auction.next_state()

        self._logger.info(f"{self._prefix}: Announcing running auction to discovery")
        mc_discovery.send(
            message=MessageAuctionAnnouncement(
                _id=generate_message_id(self._auction.get_id()),
                auction=AuctionMessageData.from_auction(self._auction),
            ).encode()
        )
        self._logger.info(f"{self._prefix}: Announced auction {self._auction.get_id()}")

    def _auction_state_changes(self) -> None:
        """Handles auction state changes.

        If the auction is running, check if the auction time is up and move the auction to the final state.
        """
        if not self._auction.is_running() or time() < self._auction.get_end_time():
            return

        self._logger.info(f"{self._prefix}: Auction time is up; moving to final state")
        self._auction.next_state()

    def _auction_announcement(self, mc_discovery: Multicast) -> None:
        """Handles auction announcements.

        Announces the auction to the discovery multicast group, if:
            - the auction is running
            - the last announcement is older than MULTICAST_AUCTION_ANNOUNCEMENT_PERIOD
            - the auction time is not up
            - OR the auction had a state change

        Args:
            mc_discovery (Multicast): Multicast object to use for sending the auction announcement.
        """
        if (
            self._auction.is_running()
            and time()
            > self._last_auction_announcement + MULTICAST_AUCTION_ANNOUNCEMENT_PERIOD
            and self._last_auction_announcement + MULTICAST_AUCTION_ANNOUNCEMENT_PERIOD
            < self._auction.get_end_time()
        ) or self._last_auction_state != self._auction.get_state():
            message: MessageAuctionAnnouncement = MessageAuctionAnnouncement(
                _id=generate_message_id(self._auction.get_id()),
                auction=AuctionMessageData.from_auction(self._auction),
            )

            mc_discovery.send(message=message.encode())

            self._last_auction_announcement = self._auction.get_end_time()
            self._logger.info(f"{self._prefix}: Sent announcement {message}")

    def _auction_state_announcement(self, mc_auction: Multicast) -> None:
        """Handles auction state changes.

        When a state change is detected, the auction manager will send an auction state announcement to the auction multicast group.
        This is done to inform all replicas of the state change.

        This method also modifies the last auction state variable.

        Args:
            mc_auction (Multicast): Multicast object to use for sending the auction state announcement.
        """
        if self._last_auction_state == self._auction.get_state():
            return

        message: MessageAuctionStateAnnouncement = MessageAuctionStateAnnouncement(
            _id=generate_message_id(self._auction.get_id()),
            state=self._auction.get_state()[0],
        )

        mc_auction.send(message=message.encode())

        self._last_auction_state = self._auction.get_state()
        self._logger.info(f"{self._prefix}: Sent state announcement {message}")

    def _auction_information_request(self, mc_receiver: Multicast) -> None:
        """Handles auction information requests.

        This includes checking, whether the auction is still running,
            a valid auction information request is received and the auction information response is sent.

        Args:
            mc_discovery (Multicast): Multicast object to use for receiving the auction information request.
        """
        try:
            message, address = mc_receiver.receive(BUFFER_SIZE)
        except TimeoutError:
            return

        if (
            not MessageSchema.of(com.HEADER_AUCTION_INFORMATION_REQ, message)
            or MessageSchema.get_id(message) in self._seen_message_id
        ):
            return

        request: MessageAuctionInformationRequest = (
            MessageAuctionInformationRequest.decode(message)
        )
        self._seen_message_id.append(request._id)

        if not request.auction and self._auction.get_id() == request.auction:
            self._logger.info(
                f"{self._prefix}: Received request {request} from {address} for another auction"
            )
            return

        self._logger.info(
            f"{self._prefix}: Received request {request} from {address} for {'all' if request.auction else 'auction ' + request.auction}"
        )
        response: MessageAuctionInformationResponse = MessageAuctionInformationResponse(
            _id=request._id,
            auction=AuctionMessageData.from_auction(self._auction),
        )
        Unicast.qsend(
            message=response.encode(),
            host=address[0],
            port=request.port,
        )
        self._logger.info(
            f"{self._prefix}: Sent response {response} to {address} for auction {self._auction.get_id()}"
        )
