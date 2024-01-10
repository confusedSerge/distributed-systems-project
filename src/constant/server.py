from util.config import load_config

_config = load_config()["server"]

REPLICA_AUCTION_POOL_SIZE = int(_config["replica"]["auction_pool_size"])
REPLICA_LOCAL_POOL_SIZE = int(_config["replica"]["local_pool_size"])
