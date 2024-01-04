import tomllib

with open("./config/config.dev.toml", "rb") as f:
    config = tomllib.load(f)

# Message Tags
FIND_REPLICA_REQUEST_TAG: str = config["message"]["find-replica-request"]
