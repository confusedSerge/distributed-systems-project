from util.config import load_config

_config = load_config()["communication"]

BUFFER_SIZE: int = int(_config["buffer_size"])

TIMEOUT_RECEIVE: float = float(_config["timeout_receive"])
TIMEOUT_RESPONSE: float = float(_config["timeout_response"])
TIMEOUT_REPLICATION: float = float(_config["timeout_replication"])
