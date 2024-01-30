# Auction States
AUCTION_PREPARATION: tuple[int, str] = (0, "Auction in preparation")
AUCTION_RUNNING: tuple[int, str] = (1, "Auction is running and accepting bids")
AUCTION_ENDED: tuple[int, str] = (2, "Auction has ended, no more bids accepted")

AUCTION_CANCELLED: tuple[int, str] = (-1, "Auction has been cancelled")


stateid2stateobj: dict[int, tuple[int, str]] = {
    0: AUCTION_PREPARATION,
    1: AUCTION_RUNNING,
    2: AUCTION_ENDED,
    -1: AUCTION_CANCELLED,
}
