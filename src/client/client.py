from time import sleep
from multiprocessing import Process, Event, Value

import inquirer

from model import AuctionAnnouncementStore
from process import Manager, AuctionAnnouncementListener

from util import create_logger, logging, Timeout
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
        super(Client, self).__init__()
        self._exit = Event()

        self.name: str = "Client"
        self.logger: logging.Logger = create_logger(self.name.lower())

        # Shared memory
        self.manager_running = Event()
        self.manager: Manager = Manager()

        self.manager.start()
        self.manager_running.set()

        self._auction_announcement_store = self.manager.AuctionAnnouncementStore()

        # Auctioneer and bidder
        self._auctioneer = Auctioneer(
            manager=self.manager,
            manager_running=self.manager_running,
            auction_announcement_store=self._auction_announcement_store,
        )
        self._bidder = Bidder(
            manager=self.manager,
            manager_running=self.manager_running,
            auction_announcement_store=self._auction_announcement_store,
        )

        # Auctioneer and bidder

    def run(self) -> None:
        """Starts the client background tasks."""
        self.logger.info(f"{self.name} is starting background tasks")

        # Start auction announcement listener
        self._auction_announcement_process = AuctionAnnouncementListener(
            self._auction_announcement_store
        )
        self._auction_announcement_process.start()

        self.logger.info(f"{self.name} started background tasks")

        while not self._exit.is_set():
            sleep(1)

        self._auctioneer.stop()
        self._bidder.stop()

        # No graceful shutdown needed, terminate all listeners
        self._auction_announcement_process.terminate()

        self.manager_running.clear()
        self.manager.shutdown()

        self.logger.info(f"{self.name} stopped background tasks")

    def stop(self) -> None:
        """Stops the client background tasks."""
        self.logger.info(f"{self.name} received stop signal")
        self._exit.set()

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

            if answer is None:
                break

            match answer["action"]:
                case "Auctioneer":
                    self._auctioneer.interact()
                case "Bidder":
                    self._bidder.interact()
                case "Stop":
                    break
                case _:
                    self.logger.error(f"Invalid action {answer}")
