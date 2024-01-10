"""This file contains all the constants related to the interaction for the interactive command line interface."""

# Client action constants
CLIENT_ACTION_QUESTION: str = "Who do you want to act as"
CLIENT_ACTION_BIDDER: str = "Bidder"
CLIENT_ACTION_AUCTIONEER: str = "Auctioneer"
CLIENT_ACTION_STOP: str = "Stop"

# Auctioneer action constants
AUCTIONEER_ACTION_QUESTION: str = "What do you want to do"
AUCTIONEER_ACTION_START: str = "Start an auction"
AUCTIONEER_ACTION_LIST_OWN_AUCTIONS: str = "List my current auctions"
AUCTIONEER_ACTION_GO_BACK: str = "Go back"

# Bidder action constants
BIDDER_ACTION_QUESTION: str = "What do you want to do"
BIDDER_ACTION_LIST_AUCTIONS: str = "List currently known active auctions"
BIDDER_ACTION_LIST_AUCTION_INFO: str = "List information about a joined auction"
BIDDER_ACTION_JOIN_AUCTION: str = "Join an auction"
BIDDER_ACTION_LEAVE_AUCTION: str = "Leave an auction"
BIDDER_ACTION_BID: str = "Bid on an auction"
BIDDER_ACTION_GO_BACK: str = "Go back"
BIDDER_BID_AMOUNT_QUESTION: str = "How much do you want to bid"
