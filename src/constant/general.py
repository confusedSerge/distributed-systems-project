from util.config import load_config

config = load_config()["general"]

SLEEP_TIME: int = int(config["sleep_time"])
