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

        self._logger.info(f"{self._name}: Initialized")

    def run(self) -> None:
        """Runs the server background tasks."""
        self._logger.info(f"{self._name}: Started")
        mc: Multicast = Multicast(
            group=MULTICAST_DISCOVERY_GROUP,
            port=MULTICAST_DISCOVERY_PORT,
            timeout=TIMEOUT_RECEIVE,
        )

        self._logger.info(f"{self._name}: Listening for replica requests")
        while not self._exit.is_set():
            try:
                message, address = mc.receive(BUFFER_SIZE)
            except TimeoutError:
                continue

            if (
                not MessageSchema.of(com.HEADER_FIND_REPLICA_REQ, message)
                or len(self._replica_pool) >= REPLICA_LOCAL_POOL_SIZE
            ):
                continue

            find_req: MessageFindReplicaRequest = MessageFindReplicaRequest.decode(
                message
            )
            self._logger.info(f"{self.name}: Replica request received: {find_req}")

            # Create replica and add to pool
            replica = Replica(
                request=find_req, sender=(IPv4Address(address[0]), find_req.port)
            )
            replica.start()
            self._replica_pool.append(replica)
            self._seen_mid.append(find_req._id)

            self._logger.info(
                f"{self._name}: Replica created and added to pool: {replica.get_id()}"
            )

        self._logger.info(f"{self._name}: Releasing resources")

        mc.close()

        # Release all replicas
        for replica in self._replica_pool:
            replica.stop()

        for replica in self._replica_pool:
            replica.join()

        self._logger.info(f"{self._name}: Stopped")

    def stop(self) -> None:
        """Stops the server."""
        self._exit.set()
        self._logger.info(f"{self._name}: Stop signal received")
