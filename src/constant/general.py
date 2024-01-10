from util.config import load_config

_config = load_config()["general"]

SLEEP_TIME: int = int(_config["sleep_time"])
