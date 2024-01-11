from util.config import load_config

_config = load_config()["communication"]["replica"]

EMMITER_PERIOD = int(_config["emitter_period"])
