from util.helper import load_config

config = load_config()["communication"]["header"]

# Message Header
FIND_REPLICA_REQ: str = config["find-replica-req"]
FIND_REPLICA_RES: str = config["find-replica-res"]
FIND_REPLICA_ACK: str = config["find-replica-ack"]

# Auction Header
AUCTION_INFORMATION_REQ: str = config["auction-information-req"]
AUCTION_INFORMATION_RES: str = config["auction-information-res"]

AUCTION_BID: str = config["auction-bid"]
AUCTION_WIN: str = config["auction-win"]
