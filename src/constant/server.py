from util.config import load_config

_config = load_config()["server"]

SERVER_POOL_SIZE: int = int(_config["pool_size"])
