from util.config import load_config

_config = load_config()["communication"]

BUFFER_SIZE: int = int(_config["buffer_size"])

TIMEOUT_RECEIVE: int = int(_config["timeout_receive"])
TIMEOUT_RESPONSE: int = int(_config["timeout_response"])
TIMEOUT_REPLICATION: int = int(_config["timeout_replication"])
