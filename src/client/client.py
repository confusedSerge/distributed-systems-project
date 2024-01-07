from multiprocessing import Process, Event

import inquirer

from util import create_logger, logging
from constant import interaction as inter

from .auctioneer import Auctioneer
from .bidder import Bidder


class Client(Process):
    """Client class for the client side of the peer-to-peer network.

    The client class runs in a separate thread (process) from the server class (normally the main thread).
    It handles the two cases of client actions; auctioneering and bidding implemented in their respective classes.

    The client actions are given through an interactive command line interface, which will cause to run the respective methods.
    """

    def __init__(self) -> None:
        """Initializes the client class."""
        super().__init__()
        self._exit = Event()

        self.name: str = "Client"
        self.logger: logging.Logger = create_logger(self.name.lower())

        self._auctioneer: Auctioneer = Auctioneer()
        self._bidder: Bidder = Bidder()

    def run(self) -> None:
        """Starts the client background tasks."""
        self.logger.info(f"{self.name} is starting background tasks")

        self._auctioneer.start()
        self._bidder.start()

        self.logger.info(f"{self.name} started background tasks")

    def stop(self) -> None:
        """Stops the client background tasks."""
        self.logger.info(f"{self.name} received stop signal")
        self._exit.set()

        self._auctioneer.stop()
        self._bidder.stop()

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
