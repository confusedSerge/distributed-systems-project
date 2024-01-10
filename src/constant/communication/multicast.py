from util.config import load_config

_config = load_config()["communication"]["multicast"]

# Multicast Discovery
DISCOVERY_GROUP = _config["discovery"]["group"]
DISCOVERY_PORT = _config["discovery"]["port"]
DISCOVERY_TTL = _config["discovery"]["ttl"]

# Multicast Auction
AUCTION_GROUP_BASE = _config["auction"]["group_base"]
AUCTION_PORT = _config["auction"]["port"]
AUCTION_TTL = _config["auction"]["ttl"]
