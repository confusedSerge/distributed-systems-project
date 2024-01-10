from ipaddress import IPv4Address, IPv4Network

from util.config import load_config

_config = load_config()["communication"]["multicast"]

# Multicast Discovery
DISCOVERY_GROUP: IPv4Address = IPv4Address(_config["discovery"]["group"])
DISCOVERY_PORT: int = int(_config["discovery"]["port"])
DISCOVERY_TTL: int = int(_config["discovery"]["ttl"])

# Multicast Auction
AUCTION_GROUP_BASE: IPv4Network = IPv4Network(_config["auction"]["group_base"])
AUCTION_PORT: int = int(_config["auction"]["port"])
AUCTION_TTL: int = int(_config["auction"]["ttl"])
