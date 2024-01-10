import tomllib

with open("./config/config.dev.toml", "rb") as f:
    config = tomllib.load(f)

# Multicast
MULTICAST_DISCOVERY_GROUP = config["multicast"]["discovery"]["group"]
MULTICAST_DISCOVERY_PORT = config["multicast"]["discovery"]["port"]
MULTICAST_DISCOVERY_TTL = config["multicast"]["discovery"]["ttl"]

# Unicast
UNICAST_DISCOVERY_PORT = config["unicast"]["discovery"]["port"]
