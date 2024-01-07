from util.helper import load_config

config = load_config()["communication"]

# Multicast Discovery
MULTICAST_DISCOVERY_GROUP = config["multicast"]["discovery"]["group"]
MULTICAST_DISCOVERY_PORT = config["multicast"]["discovery"]["port"]
MULTICAST_DISCOVERY_TTL = config["multicast"]["discovery"]["ttl"]

# Unicast Communication
UNICAST_PORT = config["unicast"]["port"]

# Message Header
HEADER_FIND_REPLICA_REQ: str = config["message"]["find-replica-req"]
HEADER_FIND_REPLICA_RES: str = config["message"]["find-replica-res"]
HEADER_FIND_REPLICA_ACK: str = config["message"]["find-replica-ack"]

# Auction Header
HEADER_AUCTION_INFORMATION_REQ: str = config["message"]["auction-information-req"]
HEADER_AUCTION_INFORMATION_RES: str = config["message"]["auction-information-res"]

HEADER_AUCTION_BID: str = config["message"]["auction-bid"]
HEADER_AUCTION_WIN: str = config["message"]["auction-win"]
