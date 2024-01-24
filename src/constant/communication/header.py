from util.config import load_config

_config = load_config()["communication"]["header"]

# Message Header
FIND_REPLICA_REQ: str = _config["replica"]["find-replica-req"]
FIND_REPLICA_RES: str = _config["replica"]["find-replica-res"]
FIND_REPLICA_ACK: str = _config["replica"]["find-replica-ack"]
PEERS_ANNOUNCEMENT: str = _config["replica"]["replica-announcement"]

# Auction Header
AUCTION_ANNOUNCEMENT: str = _config["auction"]["auction-announcement"]

AUCTION_INFORMATION_REQ: str = _config["auction"]["auction-information-req"]
AUCTION_INFORMATION_RES: str = _config["auction"]["auction-information-res"]
AUCTION_INFORMATION_ACK: str = _config["auction"]["auction-information-ack"]

AUCTION_BID: str = _config["auction"]["auction-bid"]
AUCTION_WIN: str = _config["auction"]["auction-win"]

# Heartbeat Header
HEARTBEAT_REQ: str = _config["heartbeat"]["heartbeat-req"]
HEARTBEAT_RES: str = _config["heartbeat"]["heartbeat-res"]

# Election Header
REELECTION_ANNOUNCEMENT: str = _config["election"]["reelection-announcement"]
ELECTION_REQ: str = _config["election"]["election-req"]
ELECTION_RES: str = _config["election"]["election-res"]
