from util.helper import load_config

config = load_config()

REPLICA_POOL_SIZE = config["replica"]["pool_size"]
