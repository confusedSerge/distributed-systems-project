from util.config import load_config

_config = load_config()["communication"]["heartbeat"]

TIMEOUT: int = int(_config["timeout"])
