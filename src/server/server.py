from ipaddress import IPv4Address
from multiprocessing import Process, Event

from communication import Multicast, MessageSchema, MessageFindReplicaRequest

from constant import (
    communication as com,
    TIMEOUT_RECEIVE,
    BUFFER_SIZE,
    MULTICAST_DISCOVERY_GROUP,
    MULTICAST_DISCOVERY_PORT,
    REPLICA_LOCAL_POOL_SIZE,
)

from util import create_logger, logger

from .replica import Replica


class Server(Process):
    """Server class.

    This class is responsible for creating the backbone of the auction system.
    It handles the following:
        - Listening for replica requests (discovery group) and creating replicas for them, if there is enough space in the pool.
    """

    def __init__(self) -> None:
        """Initializes the server class."""
        super(Server, self).__init__()
        self._exit: Event = Event()

        self._name: str = "Server"
        self._logger: logger = create_logger(self._name.lower())

        self._replica_pool: list[Replica] = []
        self._seen_mid: list[
            str
        ] = []  # List of seen message ids, to prevent duplicate replicas

        self._logger.info(f"{self._name} initialized")

    def run(self) -> None:
        """Runs the server background tasks."""
        self._logger.info(f"{self._name} starting background tasks")
        mc: Multicast = Multicast(
            group=MULTICAST_DISCOVERY_GROUP,
            port=MULTICAST_DISCOVERY_PORT,
            timeout=TIMEOUT_RECEIVE,
        )

        while not self._exit.is_set():
            try:
                request, address = mc.receive(BUFFER_SIZE)
            except TimeoutError:
                continue

            if (
                not MessageSchema.of(com.HEADER_FIND_REPLICA_REQ, request)
                or len(self._replica_pool) >= REPLICA_LOCAL_POOL_SIZE
            ):
                continue

            request = MessageFindReplicaRequest.decode(request)
            self._logger.info(f"Received replica request from {address}")

            # Create replica and add to pool
            replica = Replica(request=request, sender=IPv4Address(address[0]))
            replica.start()
            self._replica_pool.append(replica)
            self._seen_mid.append(request._id)

            self._logger.info(
                f"Created replica {replica.get_id()} for Replica Request {request._id}"
            )

        self._logger.info("Server received stop signal; releasing resources")

        mc.close()

        # Release all replicas
        for replica in self._replica_pool:
            replica.stop()

        for replica in self._replica_pool:
            replica.join()

        self._logger.info("Server stopped")

    def stop(self) -> None:
        """Stops the server."""
        self._exit.set()
        self._logger.info("Server received stop signal")
