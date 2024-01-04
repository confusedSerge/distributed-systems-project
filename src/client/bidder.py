import inquirer

from constant import interaction as inter


class Bidder:
    """The bidder class handles the bidding process of the client.

    The bidder class is responsible for the following:
    - Joining as a bidder: The bidder sends a discovery message to the multicast group to find auctions and keeps listening for auction announcements (background process for listening).
    - Joining an auction: The bidder joins the auction by joining the multicast group of the auction
        and starts listening for messages from the auction, keeping track of the highest bid and announcements of the winner.
    - Bidding: The bidder sends a bid to the auction by sending a message to the multicast group of the auction containing the bid.
    - Leaving an auction: The bidder leaves the auction by leaving the multicast group of the auction, and stops listening for messages from the auction.
    - Leaving as a bidder: The bidder leaves the multicast group, stops listening for auction announcements and clears the list of auctions.
    """

    def __init__(self) -> None:
        """Initializes the bidder class."""
        self.auctions = []

    def run(self) -> None:
        """Runs the bidder background tasks."""
        pass

    def interact(self) -> None:
        """Handles the interactive command line interface for the bidder.

        This should be run in the main thread (process), handling user input.
        """
        while True:
            answer = inquirer.prompt(
                [
                    inquirer.List(
                        "action",
                        message=inter.BIDDER_ACTION_QUESTION,
                        choices=[
                            inter.BIDDER_ACTION_LIST_AUCTIONS,
                            inter.BIDDER_ACTION_JOIN_AUCTION,
                            inter.BIDDER_ACTION_LEAVE_AUCTION,
                            inter.BIDDER_ACTION_BID,
                            inter.BIDDER_ACTION_GO_BACK,
                        ],
                    )
                ]
            )

            match answer["action"]:
                case inter.BIDDER_ACTION_LIST_AUCTIONS:
                    pass
                case inter.BIDDER_ACTION_JOIN_AUCTION:
                    pass
                case inter.BIDDER_ACTION_LEAVE_AUCTION:
                    pass
                case inter.BIDDER_ACTION_BID:
                    pass
                case inter.BIDDER_ACTION_GO_BACK:
                    break
                case _:
                    pass