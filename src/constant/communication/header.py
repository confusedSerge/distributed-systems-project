from util.config import load_config

config = load_config()["communication"]["header"]

# Message Header
FIND_REPLICA_REQ: str = config["replica"]["find-replica-req"]
FIND_REPLICA_RES: str = config["replica"]["find-replica-res"]
FIND_REPLICA_ACK: str = config["replica"]["find-replica-ack"]

# Auction Header
AUCTION_ANNOUNCEMENT: str = config["auction"]["auction-announcement"]

AUCTION_INFORMATION_REQ: str = config["auction"]["auction-information-req"]
AUCTION_INFORMATION_RES: str = config["auction"]["auction-information-res"]

AUCTION_BID: str = config["auction"]["auction-bid"]
AUCTION_WIN: str = config["auction"]["auction-win"]
