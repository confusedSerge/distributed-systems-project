import time

from util.logger import create_logger


class Server:
    """Server class.

    This class is responsible for creating the backbone of the auction system.
    As it is run completely in the background, using logging to keep track of what is happening.
    It handles the following:
        - Listening for replica requests (discovery group) and creating replicas for them, if there is enough space in the pool.
    """

    def __init__(self) -> None:
        """Initializes the server class."""
        self.logger = create_logger("server")

    def run(self) -> None:
        """Runs the server background tasks."""
        self.logger.info("Server is starting background tasks")
        while True:
            time.sleep(10)
            self.logger.info("Server is running background tasks")
