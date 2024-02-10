from multiprocessing import Event as ProcessEvent
from multiprocessing.synchronize import Event

from logging import Logger

import inquirer

# === Custom Modules ===

from model import AuctionAnnouncementStore
from process import Manager, AuctionAnnouncementListener

from util import create_logger
from constant import interaction as inter

# === Local Modules ===

from .auctioneer import Auctioneer
from .bidder import Bidder


class Client:
    """Client class for the client side of the peer-to-peer network.

    It handles the two cases of client actions; auctioneering and bidding implemented in their respective classes.

    The client actions are given through an interactive command line interface, which will cause to run the respective methods.
    """

    def __init__(self) -> None:
        """Initializes the client class."""
        super(Client, self).__init__()
        self._exit: Event = ProcessEvent()

        self._name: str = self.__class__.__name__.lower()
        self._prefix: str = f"{self._name}"
        self._logger: Logger = create_logger(self._name.lower())

        # Shared memory
        self.manager: Manager = Manager()
        self.manager_running: Event = ProcessEvent()

        self.manager.start()
        self.manager_running.set()

        self.auction_announcement_store: AuctionAnnouncementStore = (
            self.manager.AuctionAnnouncementStore()  # type: ignore
        )

        # Auctioneer and bidder
        self._auctioneer: Auctioneer = Auctioneer(
            manager=self.manager,
            manager_running=self.manager_running,
            auction_announcement_store=self.auction_announcement_store,
        )
        self._bidder: Bidder = Bidder(
            manager=self.manager,
            manager_running=self.manager_running,
            auction_announcement_store=self.auction_announcement_store,
        )

        self._logger.info(f"{self._prefix}: Initialized")

    def run(self) -> None:
        """Starts the client background tasks."""
        self._logger.info(f"{self._prefix}: Started")

        self._prelude()

        self._logger.info(
            f"{self._prefix}: Starting interactive command line interface"
        )
        self.interact()

        self._shutdown()
        self._logger.info(f"{self._prefix}: Stopped")

    def stop(self) -> None:
        """Stops the client background tasks."""
        self._exit.set()
        self._logger.info(f"{self._prefix}: Stopping")

    def interact(self) -> None:
        """Handles the interactive command line interface for the client.

        This should be run in the main thread (process), handling user input.
        """
        while not self._exit.is_set():
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
                case inter.CLIENT_ACTION_AUCTIONEER:
                    self._auctioneer.interact()
                case inter.CLIENT_ACTION_BIDDER:
                    self._bidder.interact()
                case inter.CLIENT_ACTION_STOP:
                    self.stop()
                case _:
                    self._logger.error(
                        f"{self._prefix}: Invalid action {answer['action']}"
                    )

    # === Helper Methods ===

    def _prelude(self):
        """Starts the client background tasks."""
        self._logger.info(f"{self._prefix}: Starting listeners")
        self._auction_announcement_process: AuctionAnnouncementListener = (
            AuctionAnnouncementListener(self.auction_announcement_store)
        )
        self._auction_announcement_process.start()

    def _shutdown(self):
        """Stops the client background tasks and releases resources."""
        self._logger.info(f"{self._prefix}: Stopping listeners and releasing resources")

        self._auctioneer.stop()
        self._bidder.stop()

        self._auction_announcement_process.stop()

        self.manager_running.clear()
        self.manager.shutdown()
        self._logger.info(f"{self._prefix}: Released resources")
