from time import sleep
from multiprocessing import Process, Event

from model import Auction
from communication import (
    Multicast,
    Unicast,
    MessageSchema,
    MessageFindReplicaRequest,
    MessageFindReplicaResponse,
    MessageFindReplicaAcknowledgement,
    AuctionMessageData,
    MessageAuctionInformationResponse,
)

from process import AuctionBidListener

from constant import (
    header as hdr,
    TIMEOUT_RECEIVE,
    TIMEOUT_REPLICATION,
    UNICAST_PORT,
)

from util import create_logger, Timeout


class Replica(Process):
    """Replica class.

    A replica is a server that is responsible for handling a single auction (in combination with other replica peers).

    A replica can be described by the following state machine:
        - Joining: The replica is joining the auction multicast group and sending a join message to the auctioneer.
        - Ready: The replica has received its peers and state of auction.
        - Timeout: The replica has did not receive its peers and state of auction in time.

        - Leader Election -> Leader: The replica is the leader of the auction.
        - Leader Election -> Follower: The replica is a follower of the auction.

        - Leader: Handles monitoring of replica peers (heartbeats), finding replicas and "auctioning" (answering incoming requests).
        - Follower: Answers heartbeat messages from the leader and starts a new election if the leader is not responding.

        - Leader and Follower: Background listener of auction.

        - Auction finished: Send winner and stop replica.
    """

    def __init__(self, request: MessageFindReplicaRequest) -> None:
        """Initializes the replica class."""
        super.__init__(self)
        self.exit = Event()

        self.request: MessageFindReplicaRequest = request
        self.auction: Auction = None
        self.peers: list[str] = []

        self.name = f"Replica-{request._id}"
        self.logger = create_logger(self.name.lower())

    def run(self) -> None:
        """Runs the replica background tasks."""
        self._prelude()

        # Start auction listener
        self.auction_listener = AuctionBidListener(self.auction)
        self.auction_listener.start()

        # Start replica leader/follower tasks (heartbeat, election, etc.)
        # TODO: impl leader/follower tasks
        while not self.exit.is_set():
            sleep(10)

        self.auction_listener.stop()

    def stop(self) -> None:
        """Stops the replica."""
        self.exit.set()
        self.logger.info("Replica received stop signal")

    def _prelude(self) -> None:
        """Handles the prelude of the replica.

        This includes:
            - Joining the auction multicast group.
            - Sending a join message to the auctioneer.
            - Waiting for the auctioneer to send the state of the auction.
            - On timeout, leave the auction multicast group and stop the replica.
        """
        # Join auction multicast group
        mc = Multicast(
            group=self.request.multicast_address[0],
            port=self.request.multicast_address[1],
            timeout=TIMEOUT_RECEIVE,
        )

        # Send join message to auctioneer
        Unicast.qsend(
            MessageFindReplicaResponse(self.request._id).encode(),
            self.request.multicast_address[0],
            self.request.multicast_address[1],
        )

        # Wait for auctioneer to acknowledge, or timeout
        uc = Unicast("", port=UNICAST_PORT)
        try:
            with Timeout(TIMEOUT_REPLICATION, throw_exception=True):
                while not self.exit.is_set():
                    response, _ = uc.receive()

                    if not MessageSchema.of(hdr.FIND_REPLICA_ACKNOWLEDGEMENT, response):
                        continue

                    response: MessageFindReplicaAcknowledgement = (
                        MessageFindReplicaAcknowledgement.decode(response)
                    )
                    if response.auction_id != self.request._id:
                        continue

                    break
        except TimeoutError:
            self.logger.info("Did not receive acknowledgement from auctioneer")
            self.stop()
            return

        try:
            with Timeout(TIMEOUT_REPLICATION, throw_exception=True):
                while not self.exit.is_set():
                    try:
                        msg, addr = mc.receive()
                    except TimeoutError:
                        continue

                    # TODO: interference possible through other
                    if not MessageSchema.of(hdr.AUCTION_INFORMATION_RES, msg):
                        continue

                    # TODO: peer list!
                    msg: MessageAuctionInformationResponse = (
                        MessageAuctionInformationResponse.decode(msg)
                    )
                    self.auction = AuctionMessageData.to_auction(
                        msg.auction_information
                    )
                    self.logger.info(
                        f"Received auction information from {addr[0]}:{addr[1]}"
                    )

                    break
        except TimeoutError:
            self.logger.info("Did not receive auction information from auctioneer")
            self.stop()
            return
