import time
import multiprocessing

from .replica import Replica

from util import create_logger, Multicast, message as msgs
from constant import communication as addr, message as msg_tag


class Server(multiprocessing.Process):
    """Server class.

    This class is responsible for creating the backbone of the auction system.
    As it is run completely in the background, using logging to keep track of what is happening.
    It handles the following:
        - Listening for replica requests (discovery group) and creating replicas for them, if there is enough space in the pool.
    """

    def __init__(self, config: dict) -> None:
        """Initializes the server class.

        Args:
            config (dict): The configuration of the client.

        """
        multiprocessing.Process.__init__(self)
        self.exit = multiprocessing.Event()

        self.logger = create_logger("server")
        self.config = config

        self.replica_pool: list[Replica] = []

    def run(self) -> None:
        """Runs the server background tasks."""
        mc_discovery_listen = Multicast(
            group=addr.MULTICAST_DISCOVERY_GROUP,
            port=addr.MULTICAST_DISCOVERY_PORT,
            sender=False,
            ttl=addr.MULTICAST_DISCOVERY_TTL,
        )

        while not self.exit.is_set():
            try:
                data, addr = mc_discovery_listen.receive()

                if msgs.decode(data)["tag"] != msg_tag.FIND_REPLICA_REQUEST_TAG:
                    continue

                decoded_msg = msgs.FindReplicaRequest.decode(data)
                self.logger.info(f"Received replica request from {addr[0]}:{addr[1]}")

                if len(self.replica_pool) >= self.config["replica"]["pool_size"]:
                    self.logger.info("Replica pool is full")
                    continue

                # Create replica and add to pool
                self.logger.info("Creating replica")
                replica = Replica(replica_request=decoded_msg)
                replica.start()

            except KeyboardInterrupt:
                self.stop()
            except Exception as e:
                self.logger.error(f"Error in server: {e}")

        # Release all replicas
        for replica in self.replica_pool:
            replica.terminate()

        # Listen for replica requests

    def stop(self) -> None:
        """Stops the server."""
        self.exit.set()
        self.logger.info("Server received stop signal")
