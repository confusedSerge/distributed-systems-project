from util.config import load_config

_config = load_config()["general"]

SLEEP_TIME: float = float(_config["sleep_time"])
