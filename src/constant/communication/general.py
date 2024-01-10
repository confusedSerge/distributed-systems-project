from util.config import load_config

config = load_config()["communication"]

BUFFER_SIZE: int = int(config["buffer_size"])

TIMEOUT_RECEIVE: int = int(config["timeout_receive"])
TIMEOUT_RESPONSE: int = int(config["timeout_response"])
TIMEOUT_REPLICATION: int = int(config["timeout_replication"])
