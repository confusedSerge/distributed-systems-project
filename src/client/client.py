import multiprocessing
import time

import inquirer

from util.helper import create_logger
from constant import interaction as inter

from .auctioneer import Auctioneer
from .bidder import Bidder


class Client(multiprocessing.Process):
    """Client class for the client side of the peer-to-peer network.

    The client class runs in a separate thread (process) from the server class.
    It handles the two cases of client actions; auctioneering and bidding implemented in their respective classes.

    The client actions are given through an interactive command line interface, which will cause to run the respective methods.
    """

    def __init__(self, config: dict) -> None:
        """Initializes the client class.

        Args:
            config (dict): The configuration of the client.

        """
        multiprocessing.Process.__init__(self)
        self.exit = multiprocessing.Event()

        self.logger = create_logger("client")
        self.config = config

        self.auctioneer = Auctioneer(config=config)
        self.bidder = Bidder(config=config)

    def run(self) -> None:
        """Runs the background tasks of the client."""
        self.logger.info("Client is starting background tasks")

        auctioneer_process = multiprocessing.Process(target=self.auctioneer.run)
        auctioneer_process.start()
        self.logger.info("Auctioneer process started")

        bidder_process = multiprocessing.Process(target=self.bidder.run)
        bidder_process.start()
        self.logger.info("Bidder process started")

        while not self.exit.is_set():
            time.sleep(10)
            self.logger.info("Client is running background tasks")

        self.logger.info("Client is terminating background tasks")
        auctioneer_process.terminate()
        bidder_process.terminate()

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
                    abort = True
                case _:
                    raise ValueError("Invalid action")

    def stop(self) -> None:
        """Stops the client."""
        self.exit.set()
        self.logger.info("Client is stopping")
