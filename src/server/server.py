from multiprocessing import Process, Event

from communication import Multicast, MessageSchema, MessageFindReplicaRequest

from constant import (
    header as hdr,
    TIMEOUT_RECEIVE,
    MULTICAST_DISCOVERY_GROUP,
    MULTICAST_DISCOVERY_PORT,
    REPLICA_LOCAL_POOL_SIZE,
)

from util import create_logger

from .replica import Replica


class Server(Process):
    """Server class.

    This class is responsible for creating the backbone of the auction system.
    It handles the following:
        - Listening for replica requests (discovery group) and creating replicas for them, if there is enough space in the pool.
    """

    def __init__(self) -> None:
        """Initializes the server class."""
        super().__init__()
        self._exit = Event()

        self.name = "Server"
        self.logger = create_logger(self.name.lower())

        self.replica_pool: list[Replica] = []

    def run(self) -> None:
        """Runs the server background tasks."""
        mc = Multicast(
            MULTICAST_DISCOVERY_GROUP, MULTICAST_DISCOVERY_PORT, timeout=TIMEOUT_RECEIVE
        )

        while not self._exit.is_set():
            try:
                request, addr = mc.receive()
            except TimeoutError:
                continue

            if (
                not MessageSchema.of(hdr.FIND_REPLICA_REQUEST, request)
                or len(self.replica_pool) >= REPLICA_LOCAL_POOL_SIZE
            ):
                continue

            request = MessageFindReplicaRequest.decode(request)
            self.logger.info(f"Received replica request from {addr[0]}:{addr[1]}")

            # Create replica and add to pool
            replica = Replica(replica_request=request)
            replica.start()
            self.replica_pool.append(replica)
            self.logger.info(f"Created replica {replica.get_id()}")

        self.logger.info("Server received stop signal; releasing resources")

        mc.close()

        # Release all replicas
        for replica in self.replica_pool:
            replica.stop()

        for replica in self.replica_pool:
            replica.join()

        self.logger.info("Server stopped")

    def stop(self) -> None:
        """Stops the server."""
        self._exit.set()
        self.logger.info("Server received stop signal")
