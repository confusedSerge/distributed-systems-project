from util.helper import load_config

config = load_config()["server"]

REPLICA_AUCTION_POOL_SIZE = int(config["replica"]["auction_pool_size"])
REPLICA_LOCAL_POOL_SIZE = int(config["replica"]["local_pool_size"])
