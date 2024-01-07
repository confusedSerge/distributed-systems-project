from util.helper import load_config

config = load_config()["communication"]["multicast"]

# Multicast Discovery
DISCOVERY_GROUP = config["discovery"]["group"]
DISCOVERY_PORT = config["discovery"]["port"]
DISCOVERY_TTL = config["discovery"]["ttl"]
