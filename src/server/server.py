import time
import multiprocessing

from util.helper import create_logger


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

    def run(self) -> None:
        """Runs the server background tasks."""
        self.logger.info("Server is starting background tasks")
        while not self.exit.is_set():
            time.sleep(10)
            self.logger.info("Server is running background tasks")

        self.logger.info("Server is terminating background tasks")

    def stop(self) -> None:
        """Stops the server."""
        self.exit.set()
        self.logger.info("Server is stopping")
