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
    MessagePeersAnnouncement,
    AuctionMessageData,
    MessageAuctionInformationResponse,
)

from model import Auction, AuctionPeersStore
from constant import (
    header as hdr,
    BUFFER_SIZE,
    TIMEOUT_REPLICATION,
    MULTICAST_DISCOVERY_GROUP,
    MULTICAST_DISCOVERY_PORT,
    MULTICAST_AUCTION_PORT,
    UNICAST_PORT,
    REPLICA_AUCTION_POOL_SIZE,
)

from util import create_logger, logger, Timeout, generate_message_id


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
        auction_peers_store: AuctionPeersStore,
        emitter_period: int = 60,
    ):
        """Initializes the replica finder process.

        Args:
            auction (Auction): The auction to find replicas for. Should be a shared memory object.
            auction_peers_store (list): The list to add the replicas to. Should be a shared memory object. Can be non-empty, representing already found replicas.
            emitter_period (int, optional): The period of the replica request emitter. Defaults to 60 seconds.
        """
        super(ReplicaFinder, self).__init__()
        self._exit: Event = Event()

        self._name: str = f"ReplicaFinder::{auction.get_id()}"
        self._logger: logger = create_logger(self._name.lower())

        self._auction: Auction = auction
        self._peers: AuctionPeersStore = auction_peers_store
        self._emitter_period: int = emitter_period

    def run(self):
        """Runs the replica finder process."""
        self._logger.info(f"{self._name} is starting background tasks")
        uc: Unicast = Unicast(host=None, port=UNICAST_PORT)

        # Start replica request emitter
        message_id: str = generate_message_id(self._auction.get_id())
        emitter: Process = Process(target=self._emit_request, args=(message_id,))
        emitter.start()

        try:
            new_replicas = self._find_replicas(uc, message_id)
        except TimeoutError:
            self._logger.info(f"{self._name} could not find enough replicas in time")
            return
        finally:
            if emitter.is_alive():
                emitter.terminate()
                emitter.join()
            uc.close()

        # Add new replica to known replicas
        try:
            self._peers.append(new_replicas)
        except ValueError:
            self._logger.info(
                f"{self._name} duplicate replica found; this should not happen"
            )
            return

        if self._exit.is_set():
            self._logger.info(f"{self._name} stopped finding replicas")
            return

        self._send_information(message_id, new_replicas)

        self._logger.info(f"{self._name} sent information to all replicas")

    def stop(self):
        """Stops the replica finder process."""
        self._logger.info(f"{self._name} received stop signal")
        self._exit.set()

    def _find_replicas(self, uc: Unicast, message_id: str) -> list[IPv4Address]:
        """Finds replicas for the auction.

        Args:
            uc (Unicast): The unicast socket.
            message_id (str): The message id to use for the find replica request.

        Returns:
            list[IPv4Address]: The list of found replicas.
        """
        seen_addresses: list[IPv4Address] = []
        new_replicas: list[IPv4Address] = []

        with Timeout(TIMEOUT_REPLICATION, throw_exception=True):
            while (
                self._peers.len() + len(new_replicas) < REPLICA_AUCTION_POOL_SIZE
                and not self._exit.is_set()
            ):
                # Receive find replica response
                response, address = uc.receive(BUFFER_SIZE)

                if not MessageSchema.of(hdr.FIND_REPLICA_RES, response):
                    continue
                response: MessageFindReplicaResponse = (
                    MessageFindReplicaResponse.decode(response)
                )

                if response._id != message_id or address[0] in seen_addresses:
                    continue

                    # Send find replica acknowledgement
                acknowledgement = MessageFindReplicaAcknowledgement(_id=message_id)
                Unicast.qsend(
                    message=acknowledgement.encode(),
                    host=IPv4Address(address[0]),
                    port=UNICAST_PORT,
                )

                # Add replica to list
                new_replicas.append(IPv4Address(address[0]))
                seen_addresses.append(IPv4Address(address[0]))

    def _send_information(self, message_id: str, new_replicas: list[IPv4Address]):
        """Sends auction information to new replicas and replica announcement to all replicas.

        Args:
            message_id (str): The message id to use for the messages.
            new_replicas (list[IPv4Address]): The list of new replicas.
        """
        # Send Auction Information to new replicas
        self._logger.info(f"{self._name} sending auction information to new replicas")
        response = MessageAuctionInformationResponse(
            _id=message_id,
            auction_information=AuctionMessageData.from_auction(self._auction),
        )
        for replica in new_replicas:
            self._logger.info(f"{self._name} sending auction information to {replica}")
            Unicast.qsend(
                message=response.encode(),
                host=replica,
                port=UNICAST_PORT,
            )

        # Send Replica Announcement to all replicas
        self._logger.info(f"{self._name} sending replica announcement to all replicas")
        for dst in self._peers:
            self._logger.info(f"{self._name} sending replica announcement to {replica}")
            response = MessagePeersAnnouncement(
                _id=message_id,
                peers=[str(replica) for replica in self._peers if replica != dst],
            )
            Unicast.qsend(
                message=response.encode(),
                host=dst,
                port=UNICAST_PORT,
            )

    def _emit_request(self, message_id: str):
        """Sends a find replica request periodically.

        Args:
            message_id (str): The message id to use for the find replica request.
        """
        mc: Multicast = Multicast(
            group=MULTICAST_DISCOVERY_GROUP, port=MULTICAST_DISCOVERY_PORT, sender=True
        )
        req: bytes = MessageFindReplicaRequest(
            _id=message_id,
            address=str(self._auction.get_multicast_address()),
        ).encode()

        while not self._exit.is_set():
            mc.send(req)
            sleep(self._emitter_period)

        mc.close()
