from util.config import load_config

_config = load_config()["auction"]

AUCTION_POOL_SIZE: int = int(_config["pool_size"])
