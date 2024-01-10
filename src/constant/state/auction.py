# Auction States
AUCTION_PREPARATION = (0, "Auction in preparation")
AUCTION_RUNNING = (1, "Auction is running and accepting bids")
AUCTION_ENDED = (2, "Auction has ended, winner is being announced")
AUCTION_WINNER_DECLARED = (3, "Auction winner has been declared")

AUCTION_CANCELLED = (-1, "Auction has been cancelled")


stateid2stateobj = {
    0: AUCTION_PREPARATION,
    1: AUCTION_RUNNING,
    2: AUCTION_ENDED,
    3: AUCTION_WINNER_DECLARED,
    -1: AUCTION_CANCELLED,
}
