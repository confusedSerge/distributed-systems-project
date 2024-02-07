from util.config import load_config

_config = load_config()["communication"]["header"]

# Wrapper Header
RELIABLE_REQ: str = _config["reliable-req"]
RELIABLE_RES: str = _config["reliable-res"]

# Message Header
FIND_REPLICA_REQ: str = _config["replica"]["find-replica-req"]
FIND_REPLICA_RES: str = _config["replica"]["find-replica-res"]

PEERS_ANNOUNCEMENT: str = _config["replica"]["peers-announcement"]

# Auction Header
AUCTION_ANNOUNCEMENT: str = _config["auction"]["auction-announcement"]
AUCTION_STATE_ANNOUNCEMENT: str = _config["auction"]["auction-state-announcement"]

AUCTION_INFORMATION_REPLICATION: str = _config["auction"][
    "auction-information-replication"
]

AUCTION_BID: str = _config["auction"]["auction-bid"]
AUCTION_WIN: str = _config["auction"]["auction-win"]

# Heartbeat Header
HEARTBEAT_REQ: str = _config["heartbeat"]["heartbeat-req"]
HEARTBEAT_RES: str = _config["heartbeat"]["heartbeat-res"]

# Election Header
ELECTION_REQ: str = _config["election"]["election-req"]
ELECTION_ANS: str = _config["election"]["election-ans"]
ELECTION_COORDINATOR: str = _config["election"]["election-coordinator"]


# Total Ordering Header
ISIS_MESSAGE_WITH_COUNTER: str = _config["total_ordering_isis"][
    "isis-message-with-counter"
]
ISIS_MESSAGE: str = _config["total_ordering_isis"]["isis-message"]
PROPOSED_SEQ: str = _config["total_ordering_isis"]["proposed-seq"]
AGREED_SEQ: str = _config["total_ordering_isis"]["agreed-seq"]
