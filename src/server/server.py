from ipaddress import IPv4Address

from multiprocessing import Process, Event as ProcessEvent
from multiprocessing.synchronize import Event

from logging import Logger

# === Custom Modules ===

from model import Auction
from communication import Multicast, MessageSchema, MessageFindReplicaRequest
from util import create_logger

from constant import (
    communication as com,
    COMMUNICATION_TIMEOUT,
    COMMUNICATION_BUFFER_SIZE,
    MULTICAST_DISCOVERY_GROUP,
    MULTICAST_DISCOVERY_PORT,
    SERVER_POOL_SIZE,
)

# === Local Modules ===

from .replica import Replica


class Server(Process):
    """Server class.

    The server is responsible for creating and managing replicas.
    This is done by listening for replica requests on a multicast group and delegating the request to a replica.
    If the server is already managing the maximum number of replicas, the request is ignored.

    """

    def __init__(self) -> None:
        """Initializes the server class."""
        super(Server, self).__init__()
        self._exit: Event = ProcessEvent()

        self._name: str = self.__class__.__name__.lower()
        self._prefix: str = f"{self._name}"
        self._logger: Logger = create_logger(self._name.lower())

        self._replica_pool: list[tuple[Replica, Event]] = []
        self._seen_auctions: list[str] = []

        self._logger.info(f"{self._prefix}: Initialized")

    def run(self) -> None:
        """
        Starts the server.
        """
        self._logger.info(f"{self._prefix}: Started")
        mc: Multicast = Multicast(
            group=MULTICAST_DISCOVERY_GROUP,
            port=MULTICAST_DISCOVERY_PORT,
            timeout=COMMUNICATION_TIMEOUT,
        )

        self._logger.info(f"{self._prefix}: Listening for replica requests")
        while not self._exit.is_set():
            try:
                message, address = mc.receive(COMMUNICATION_BUFFER_SIZE)
            except TimeoutError:
                # Check if process can be removed from pool
                for replica, stopped in self._replica_pool:
                    if stopped.is_set():
                        self._logger.info(
                            f"{self._prefix}: Replica stopped and removed from pool: {replica.get_id()}"
                        )
                        self._replica_pool.remove((replica, stopped))
                        break
                continue

            # Ignore if message is not a replica request, if the pool is full, or if the message has already been seen
            if (
                not MessageSchema.of(com.HEADER_FIND_REPLICA_REQ, message)
                or len(self._replica_pool) >= SERVER_POOL_SIZE
            ):
                continue

            # Convert message to replica request
            find_req: MessageFindReplicaRequest = MessageFindReplicaRequest.decode(
                message
            )
            self._logger.info(
                f"{self.name}: Replica request received: {find_req} from Multicast {address}"
            )

            try:
                auction_id = Auction.parse_id(find_req._id)
            except ValueError:
                self._logger.error(
                    f"{self._prefix}: Invalid auction id for message: {find_req}"
                )
                continue

            if auction_id in self._seen_auctions:
                self._logger.info(
                    f"{self._prefix}: Ignoring request for auction {auction_id} as it has already been seen"
                )
                continue

            # Create replica and add to pool
            stopped_processes: Event = ProcessEvent()
            replica = Replica(
                request=find_req,
                sender=(IPv4Address(address[0]), find_req.port),
                stopped=stopped_processes,
            )
            replica.start()
            self._replica_pool.append((replica, stopped_processes))
            self._seen_auctions.append(auction_id)

            self._logger.info(
                f"{self._prefix}: Replica created and added to pool: {replica.get_id()}"
            )

            self._logger.info(
                f"{self._prefix}: Replica in pool: {len(self._replica_pool)}"
            )

        # Stop listening for replica requests
        self._logger.info(f"{self._prefix}: Releasing resources")
        mc.close()

        # Release all replicas
        for replica, stopped in self._replica_pool:
            replica.stop()

        self._logger.info(f"{self._prefix}: Stopped")

    def stop(self) -> None:
        """Stops the server."""
        self._exit.set()
        self._logger.info(f"{self._prefix}: Stop signal received")
