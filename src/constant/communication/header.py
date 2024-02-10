from util.config import load_config

_config = load_config()["communication"]["header"]

# Wrapper Header
RELIABLE_REQ: str = _config["reliable-req"]
RELIABLE_RES: str = _config["reliable-res"]
RELIABLE_MULTICAST: str = _config["reliable-multicast"]

# ISIS Total Ordering Header
ISIS_MESSAGE: str = _config["isis"]["isis-message"]
ISIS_PROPOSED_SEQ: str = _config["isis"]["proposed-seq"]
ISIS_AGREED_SEQ: str = _config["isis"]["agreed-seq"]

# Replica Header
FIND_REPLICA_REQ: str = _config["replica"]["find-req"]
FIND_REPLICA_RES: str = _config["replica"]["find-res"]

# Heartbeat Header
HEARTBEAT_REQ: str = _config["heartbeat"]["req"]
HEARTBEAT_RES: str = _config["heartbeat"]["res"]

# Election Header
ELECTION_REQ: str = _config["election"]["req"]
ELECTION_ANS: str = _config["election"]["ans"]
ELECTION_COORDINATOR: str = _config["election"]["coordinator"]

# Auction Header
AUCTION_ANNOUNCEMENT: str = _config["auction"]["announcement"]

AUCTION_INFORMATION_REPLICATION: str = _config["auction"]["information-replication"]
AUCTION_STATE_ANNOUNCEMENT: str = _config["auction"]["state-announcement"]
AUCTION_PEERS_ANNOUNCEMENT: str = _config["auction"]["peers-announcement"]
AUCTION_BID: str = _config["auction"]["bid"]
