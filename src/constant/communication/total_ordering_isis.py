from util.config import load_config

_config = load_config()["communication"]["total_ordering_isis"]

TIMEOUT: int = int(_config["timeout"])
