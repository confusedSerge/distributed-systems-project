import tomllib

with open("./config/config.dev.toml", "rb") as f:
    config = tomllib.load(f)

# Message Tags
FIND_REPLICA_REQUEST_TAG: str = config["message"]["find-replica-request"]
FIND_REPLICA_RESPONSE_TAG: str = config["message"]["find-replica-response"]
FIND_REPLICA_ACK_TAG: str = config["message"]["find-replica-ack"]

AUCTION_REPLICA_PEERS_TAG: str = config["message"]["auction-replica-peers"]

AUCTION_ANNOUNCEMENT_TAG: str = config["message"]["auction-announcement"]
