import multiprocessing

import inquirer

from util.helper import create_logger, logging
from constant import interaction as inter

from .auctioneer import Auctioneer
from .bidder import Bidder


class Client:
    """Client class for the client side of the peer-to-peer network.

    The client class runs in a separate thread (process) from the server class (normally the main thread).
    It handles the two cases of client actions; auctioneering and bidding implemented in their respective classes.

    The client actions are given through an interactive command line interface, which will cause to run the respective methods.
    """

    def __init__(self, config: dict) -> None:
        """Initializes the client class.

        Args:
            config (dict): The configuration of the client.

        """
        self.name: str = "Client"

        self.logger: logging.Logger = create_logger(self.name.lower())
        self.config: dict = config

        self.background: multiprocessing.Process = None
        self.auctioneer: Auctioneer = Auctioneer(config=config)
        self.bidder: Bidder = Bidder(config=config)

    def start(self) -> None:
        """Starts the client background tasks."""
        self.logger.info(f"{self.name} is starting background tasks")

        self.auctioneer.start()
        self.bidder.start()

        self.background = multiprocessing.Process(target=self._background)

        self.logger.info(f"{self.name} started background tasks")

    def _background(self) -> None:
        """Handles the client background tasks."""
        pass

    def stop(self) -> None:
        """Stops the client background tasks."""
        self.logger.info(f"{self.name} is stopping background tasks")

        self.auctioneer.stop()
        self.bidder.stop()

        if self.background is not None and self.background.is_alive():
            self.background.terminate()

        self.logger.info(f"{self.name} stopped background tasks")

    def interact(self) -> None:
        """Handles the interactive command line interface for the client.

        This should be run in the main thread (process), handling user input.
        """
        while True:
            answer = inquirer.prompt(
                [
                    inquirer.List(
                        "action",
                        message=inter.CLIENT_ACTION_QUESTION,
                        choices=[
                            inter.CLIENT_ACTION_AUCTIONEER,
                            inter.CLIENT_ACTION_BIDDER,
                            inter.CLIENT_ACTION_STOP,
                        ],
                    )
                ]
            )

            match answer["action"]:
                case "Auctioneer":
                    self.auctioneer.interact()
                case "Bidder":
                    self.bidder.interact()
                case "Stop":
                    break
                case _:
                    self.logger.error(f"Invalid action {answer['action']}")
