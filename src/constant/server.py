from util.helper import load_config

config = load_config()["server"]

REPLICA_POOL_SIZE = int(config["replica"]["pool_size"])
