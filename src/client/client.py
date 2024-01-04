import time
import inquirer

from util.logger import create_logger

from .auctioneer import Auctioneer
from .bidder import Bidder


class Client:
    """Client class for the client side of the peer-to-peer network.

    The client class runs in a separate thread (process) from the server class.
    It handles the two cases of client actions; auctioneering and bidding implemented in their respective classes.

    The client actions are given through an interactive command line interface, which will cause to run the respective methods.
    """

    def __init__(self) -> None:
        """Initializes the client class."""
        self.logger = create_logger("client")

        self.auctioneer = Auctioneer()
        self.bidder = Bidder()

    def run(self) -> None:
        """Runs the background tasks of the client."""
        self.logger.info("Client is starting background tasks")
        while True:
            time.sleep(10)
            self.logger.info("Client is running background tasks")

    def interact(self) -> None:
        """Handles the interactive command line interface for the client.

        This should be run in the main thread (process), handling user input.
        """
        abort = False
        while not abort:
            answer = inquirer.prompt(
                [
                    inquirer.List(
                        "action",
                        message="What do you want to do?",
                        choices=["Auctioneer", "Bidder", "Abort"],
                    )
                ]
            )

            match answer["action"]:
                case "Auctioneer":
                    self.auctioneer.interact()
                case "Bidder":
                    self.bidder.interact()
                case "Abort":
                    abort = True
                case _:
                    raise ValueError("Invalid action")
