from util.config import load_config

_config = load_config()["communication"]["replica"]

EMITTER_PERIOD = int(_config["emitter_period"])
TIMEOUT_REPLICATION: int = int(_config["timeout"])
