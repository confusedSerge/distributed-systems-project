from util.config import load_config

_config = load_config()["communication"]["multicast"]

# Multicast Discovery
DISCOVERY_GROUP = _config["discovery"]["group"]
DISCOVERY_PORT = _config["discovery"]["port"]
DISCOVERY_TTL = _config["discovery"]["ttl"]
