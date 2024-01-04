class Auctioneer:
    """Auctioneer class handles the auctioning of items, keeping track of the highest bid and announcing the winner.

    The auctioneer class is responsible for the following:
    - Creating an auction: The auctioneer creates an auction by defining the item, price and time and starting the auction (delegating to sub-auctioneer).
    - List all auctions: The auctioneer lists all auctions currently running.
    - Information about an auction: The auctioneer lists information about a specific auction.
    """

    def __init__(self) -> None:
        """Initializes the auctioneer class."""
        pass

    def run(self) -> None:
        """Runs the auctioneer background tasks."""
        pass

    def interact(self) -> None:
        """Handles the interactive command line interface for the auctioneer.

        This should be run in the main thread (process), handling user input.
        """
        print("Auctioneer")


class _SubAuctioneer:
    """Sub-Auctioneer class handles the auctioning of items, keeping track of the highest bid and announcing the winner.

    The sub-auctioneer is run in a separate thread (process) from the auctioneer, for each auction the client creates.
    It handles the prelude by defining the item, price and time, finding replicas
        and starting the auction by informing the replicas of other replicas and sending an announcement of the auction to the discovery group.
    If not enough replicas are found, the auction is cancelled. This is handled by a timeout.
    After the prelude, the sub-auctioneer continues to listen on the multicast group for bids and keeps track of the auction.
    When the auction is over, the sub-auctioneer leaves the multicast group.
    """
