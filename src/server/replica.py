import multiprocessing

from model import Auction

from util import create_logger, Multicast, Unicast, message as msgs, listen_auction
from constant import addresses as addr, message as msg_tag


class Replica(multiprocessing.Process):
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

    def __init__(self, replica_request: msgs.FindReplicaRequest) -> None:
        """Initializes the replica class."""
        multiprocessing.Process.__init__(self)
        self.exit = multiprocessing.Event()

        self.logger = create_logger("replica")

        self.replica_request: msgs.FindReplicaRequest = replica_request

        self.auction: Auction = None

        self.peers: list[str] = []

        self.leader_election = multiprocessing.Event()
        self.leader: bool = False
        self.leader_address: tuple[str, int] = None

        self.auction_listener: multiprocessing.Process = None

    def run(self) -> None:
        """Runs the replica background tasks."""
        self._prelude()

        # Start auction listener
        self.auction_listener = multiprocessing.Process(
            target=listen_auction, args=(self.auction,)
        )
        self.auction_listener.start()

        # Start replica leader/follower tasks
        # TODO: This is a temporary stub placeholder, as not yet implemented
        # TODO: This should be a separate process defined by a class
        while not self.exit.is_set():
            self._leader_election()
            if self.leader:
                self._leader()
            else:
                self._follower()

    def _prelude(self) -> None:
        """Handles the prelude of the replica.

        This includes:
            - Joining the auction multicast group.
            - Sending a join message to the auctioneer.
            - Waiting for the auctioneer to send the state of the auction.
            - On timeout, leave the auction multicast group and stop the replica.
        """
        # Join auction multicast group
        mc_auction_listen = Multicast(
            group=self.replica_request.auctioneer_address,
            port=self.replica_request.auctioneer_port,
            sender=False,
            ttl=1,
        )

        # Send join message to auctioneer
        uc_auctioneer_send = Unicast(
            address=self.replica_request.auctioneer_address,
            port=self.replica_request.auctioneer_port,
        )
        uc_auctioneer_send.send(
            msgs.FindReplicaResponse(_id=self.replica_request._id).encode()
        )

        # Wait for auctioneer to send auction information and peers
        while not self.exit.is_set():
            data, addr = mc_auction_listen.receive()

            if msgs.decode(data)["tag"] != msg_tag.AUCTION_REPLICA_PEERS_TAG:
                continue

            # TODO: Assume this also contains the auction information
            decoded_msg: msgs.AuctionReplicaPeers = msgs.AuctionReplicaPeers.decode(
                data
            )
            self.logger.info(f"Received auction information from {addr[0]}:{addr[1]}")

            # Create auction
            self.auction = Auction(
                item="",
                price=0,
                time=0,
                _id=decoded_msg._id,
                multicast_group=decoded_msg.multicast_group,
                multicast_port=decoded_msg.multicast_port,
            )

            break
