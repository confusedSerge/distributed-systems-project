from time import sleep
from multiprocessing import Process, Event, Value

import inquirer

from model import AuctionAnnouncementStore
from process import Manager, AuctionAnnouncementListener

from util import create_logger, logging, Timeout
from constant import interaction as inter, SLEEP_TIME

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

        self._name: str = "Client"
        self._logger: logging.Logger = create_logger(self._name.lower())

        # Shared memory
        self.manager: Manager = Manager()
        self.manager_running: Event = Event()

        self.manager.start()
        self.manager_running.set()

        self.auction_announcement_store = self.manager.AuctionAnnouncementStore()

        # Auctioneer and bidder
        self._auctioneer = Auctioneer(
            manager=self.manager,
            manager_running=self.manager_running,
            auction_announcement_store=self.auction_announcement_store,
        )
        self._bidder = Bidder(
            manager=self.manager,
            manager_running=self.manager_running,
            auction_announcement_store=self.auction_announcement_store,
        )

        self._logger.info(f"{self._name} initialized")

    def run(self) -> None:
        """Starts the client background tasks."""
        self._logger.info(f"{self._name} is starting background tasks")

        # Start auction announcement listener
        self._auction_announcement_process = AuctionAnnouncementListener(
            self.auction_announcement_store
        )
        self._auction_announcement_process.start()

        self._logger.info(f"{self._name} started background tasks")

        while not self._exit.is_set():
            sleep(SLEEP_TIME)

        self._auctioneer.stop()
        self._bidder.stop()

        # No graceful shutdown needed, terminate all listeners
        self._auction_announcement_process.stop()

        self.manager_running.clear()
        self.manager.shutdown()

        self._logger.info(f"{self._name} stopped background tasks")

    def stop(self) -> None:
        """Stops the client background tasks."""
        self._logger.info(f"{self._name} received stop signal")
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
                    self._logger.error(f"Invalid action {answer}")
