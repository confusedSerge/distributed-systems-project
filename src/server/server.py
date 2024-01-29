from ipaddress import IPv4Address

from multiprocessing import Process, Event as ProcessEvent
from multiprocessing.synchronize import Event

from logging import Logger

# === Custom Modules ===

from communication import Multicast, MessageSchema, MessageFindReplicaRequest
from util import create_logger

from constant import (
    communication as com,
    TIMEOUT_RECEIVE,
    BUFFER_SIZE,
    MULTICAST_DISCOVERY_GROUP,
    MULTICAST_DISCOVERY_PORT,
    REPLICA_LOCAL_POOL_SIZE,
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

        self._name: str = "Server"
        self._logger: Logger = create_logger(self._name.lower())

        self._replica_pool: list[Replica] = []
        self._seen_message_ids: list[str] = []

        self._logger.info(f"{self._name}: Initialized")

    def run(self) -> None:
        """
        Starts the server.
        """
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

            # Ignore if message is not a replica request, if the pool is full, or if the message has already been seen
            if (
                not MessageSchema.of(com.HEADER_FIND_REPLICA_REQ, message)
                or len(self._replica_pool) >= REPLICA_LOCAL_POOL_SIZE
                or MessageSchema.get_id(message) in self._seen_message_ids
            ):
                continue

            # Convert message to replica request
            find_req: MessageFindReplicaRequest = MessageFindReplicaRequest.decode(
                message
            )
            self._logger.info(
                f"{self.name}: Replica request received: {find_req} from Multicast {address}"
            )

            # Create replica and add to pool
            replica = Replica(
                request=find_req, sender=(IPv4Address(address[0]), find_req.port)
            )
            replica.start()
            self._replica_pool.append(replica)
            self._seen_message_ids.append(find_req._id)

            self._logger.info(
                f"{self._name}: Replica created and added to pool: {replica.get_id()}"
            )

        # Stop listening for replica requests
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
