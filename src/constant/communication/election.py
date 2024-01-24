from util.config import load_config

_config = load_config()["communication"]["election"]

TIMEOUT: int = int(_config["timeout"])
