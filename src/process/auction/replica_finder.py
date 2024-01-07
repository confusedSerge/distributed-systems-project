from time import sleep
from multiprocessing import Process, Event

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

from model import Auction
from constant import (
    header as hdr,
    MULTICAST_DISCOVERY_GROUP,
    MULTICAST_DISCOVERY_PORT,
    UNICAST_PORT,
    REPLICA_AUCTION_POOL_SIZE,
)

from util import create_logger


class ReplicaFinder(Process):
    """Handles the finding of replicas for an auction.

    The replica finder process runs in the background as follows:
    - Sends a find replica request to the discovery multicast group.
    - Receives find replica responses from the default unicast port.
    - Sends a find replica acknowledgement to the response sender.
    - Adds the response sender to the replica list.
    - Repeats until the replica list is full.

    The replica request is send periodically until the replica list is full.
    """

    def __init__(self, auction: Auction, replicas_list: list, emitter_period: int = 60):
        """Initializes the replica finder process.

        Args:
            auction (Auction): The auction to find replicas for. Should be a shared memory object.
            replicas_list (list): The list to add the replicas to. Should be a shared memory object. Can be non-empty, representing already found replicas.
            emitter_period (int, optional): The period of the replica request emitter. Defaults to 60 seconds.
        """
        super().__init__()
        self._exit = Event()

        self._auction: Auction = auction
        self._replicas_list: list = replicas_list
        self._emitter_period: int = emitter_period

        self.name = f"ReplicaFinder-{auction.get_id()}"
        self.logger = create_logger(self.name.lower())

    def run(self):
        """Runs the replica finder process."""
        self.logger.info(f"{self.name} is starting background tasks")
        uc: Unicast = Unicast("", port=UNICAST_PORT, sender=False)

        # Start replica request emitter
        emitter = Process(target=self._emit_request)
        emitter.start()

        new_replicas: list[str] = []
        while (
            len(self._replicas_list) + len(new_replicas) < REPLICA_AUCTION_POOL_SIZE
            and not self._exit.is_set()
        ):
            # Receive find replica response
            response, address = uc.receive()

            if not MessageSchema.of(hdr.FIND_REPLICA_RESPONSE, response):
                continue
            response: MessageFindReplicaResponse = MessageFindReplicaResponse.decode(
                response
            )

            # TODO: Check if auction is still running
            # TODO: Keep track of response already received and added before
            if response.auction_id != self._auction.get_id():
                continue

            # Send find replica acknowledgement
            Unicast.qsend(
                MessageFindReplicaAcknowledgement(
                    auction_id=self._auction.get_id()
                ).encode(),
                address,
                UNICAST_PORT,
            )

            # Add replica to list
            self._replicas_list.append(address)
            new_replicas.append(address)

        if (
            not self._exit.is_set()
            and len(self._replicas_list) + len(new_replicas)
            >= REPLICA_AUCTION_POOL_SIZE
            and emitter.is_alive()
        ):
            self.logger.info(f"{self.name} found enough replicas, stopping emitter")
            emitter.terminate()

        # Send Auction Information to new replicas
        for replica in new_replicas:
            self.logger.info(
                f"{self.name} sending auction information to new replica {replica}"
            )
            Unicast.qsend(
                MessageAuctionInformationResponse(
                    _id=self._auction.get_id(),
                    auction_information=AuctionMessageData.from_auction(self._auction),
                ).encode(),
                replica,
                UNICAST_PORT,
            )

        self.logger.info(f"{self.name} stopped finding replicas")

    def stop(self):
        """Stops the replica finder process."""
        self.logger.info(f"{self.name} received stop signal")
        self.event.set()

    def _emit_request(self):
        """Sends a find replica request periodically."""
        mc: Multicast = Multicast(MULTICAST_DISCOVERY_GROUP, MULTICAST_DISCOVERY_PORT)
        req: MessageFindReplicaRequest = MessageFindReplicaRequest(
            auction_id=self._auction.get_id(),
            auction_multicast_group=self._auction.get_multicast_group(),
            auction_multicast_port=self._auction.get_multicast_port(),
        )

        while not self._exit.is_set():
            mc.send(req.encode())
            sleep(self._emitter_period)

        mc.close()
