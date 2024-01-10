from ipaddress import IPv4Address

from multiprocessing import Process, Event
from time import sleep

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
    TIMEOUT_REPLICATION,
    MULTICAST_DISCOVERY_GROUP,
    MULTICAST_DISCOVERY_PORT,
    MULTICAST_AUCTION_PORT,
    UNICAST_PORT,
    REPLICA_AUCTION_POOL_SIZE,
)

from util import create_logger, Timeout


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

    def __init__(
        self,
        auction: Auction,
        replicas_list: list[IPv4Address],
        emitter_period: int = 60,
    ):
        """Initializes the replica finder process.

        Args:
            auction (Auction): The auction to find replicas for. Should be a shared memory object.
            replicas_list (list): The list to add the replicas to. Should be a shared memory object. Can be non-empty, representing already found replicas.
            emitter_period (int, optional): The period of the replica request emitter. Defaults to 60 seconds.
        """
        super().__init__()
        self._exit = Event()

        self._name = f"ReplicaFinder-{auction.get_id()}"
        self._logger = create_logger(self._name.lower())

        self._auction: Auction = auction
        self._replicas_list: list[IPv4Address] = replicas_list
        self._emitter_period: int = emitter_period

    def run(self):
        """Runs the replica finder process."""
        self._logger.info(f"{self._name} is starting background tasks")
        uc: Unicast = Unicast(host=None, port=UNICAST_PORT)

        # Start replica request emitter
        emitter = Process(target=self._emit_request)
        emitter.start()

        new_replicas: list[str] = []
        try:
            with Timeout(TIMEOUT_REPLICATION, throw_exception=True):
                while (
                    len(self._replicas_list) + len(new_replicas)
                    < REPLICA_AUCTION_POOL_SIZE
                    and not self._exit.is_set()
                ):
                    # Receive find replica response
                    response, address = uc.receive()

                    if not MessageSchema.of(hdr.FIND_REPLICA_RESPONSE, response):
                        continue
                    response: MessageFindReplicaResponse = (
                        MessageFindReplicaResponse.decode(response)
                    )

                    # TODO: Check if auction is still running
                    # TODO: Keep track of response already received and added before
                    if response.auction_id != self._auction.get_id():
                        continue

                    # Send find replica acknowledgement
                    acknowledgement = MessageFindReplicaAcknowledgement(
                        auction_id=self._auction.get_id()
                    )
                    Unicast.qsend(
                        message=acknowledgement.encode(),
                        host=IPv4Address(address[0]),
                        port=UNICAST_PORT,
                    )

                    # Add replica to list
                    self._replicas_list.append(IPv4Address(address[0]))
                    new_replicas.append(IPv4Address(address[0]))

        except TimeoutError:
            self._logger.info(f"{self._name} could not find enough replicas in time")
            return
        finally:
            if emitter.is_alive():
                emitter.terminate()
                emitter.join()
            uc.close()

        if self._exit.is_set():
            self._logger.info(f"{self._name} stopped finding replicas")
            return

        # Send Auction Information to new replicas
        for replica in new_replicas:
            self._logger.info(
                f"{self._name} sending auction information to new replica {replica}"
            )
            response = MessageAuctionInformationResponse(
                _id=self._auction.get_id(),
                auction_information=AuctionMessageData.from_auction(self._auction),
            )
            Unicast.qsend(
                message=response.encode(),
                host=replica,
                port=UNICAST_PORT,
            )

        self._logger.info(f"{self._name} sent auction information to all new replicas")

    def stop(self):
        """Stops the replica finder process."""
        self._logger.info(f"{self._name} received stop signal")
        self._exit.set()

    def _emit_request(self):
        """Sends a find replica request periodically."""
        mc: Multicast = Multicast(
            group=MULTICAST_DISCOVERY_GROUP, port=MULTICAST_DISCOVERY_PORT, sender=True
        )
        req: MessageFindReplicaRequest = MessageFindReplicaRequest(
            auction_id=self._auction.get_id(),
            auction_multicast_group=self._auction.get_multicast_address(),
            auction_multicast_port=MULTICAST_AUCTION_PORT,
        )

        while not self._exit.is_set():
            mc.send(req.encode())
            sleep(self._emitter_period)

        mc.close()
