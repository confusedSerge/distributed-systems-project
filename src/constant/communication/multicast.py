from ipaddress import IPv4Address, IPv4Network

from util.config import load_config

_config = load_config()["communication"]["multicast"]

# Multicast Discovery
DISCOVERY_GROUP: IPv4Address = IPv4Address(_config["discovery"]["group"])
DISCOVERY_PORT: int = int(_config["discovery"]["port"])
DISCOVERY_TTL: int = int(_config["discovery"]["ttl"])

# Multicast Auction
_auction = _config["auction"]

AUCTION_GROUP_BASE: IPv4Network = IPv4Network(_auction["group_base"])
AUCTION_PORT: int = int(_auction["port"])
AUCTION_TTL: int = int(_auction["ttl"])

# Auction Announcement
AUCTION_ANNOUNCEMENT_PORT: int = int(_auction["announcement"]["port"])
AUCTION_ANNOUNCEMENT_PERIOD: int = int(_auction["announcement"]["period_base"])
AUCTION_ANNOUNCEMENT_PERIOD_HF: int = int(_auction["announcement"]["period_hf"])

# Auction Peers Announcement
AUCTION_PEERS_ANNOUNCEMENT_PORT: int = int(_auction["peers"]["port"])

# Auction State Announcement
AUCTION_STATE_ANNOUNCEMENT_PORT: int = int(_auction["state"]["port"])

# Auction Bid
AUCTION_BID_PORT: int = int(_auction["bid"]["port"])
