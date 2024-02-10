from util.config import load_config

_config = load_config()["communication"]

TIMEOUT: int = int(_config["timeout"])
BUFFER_SIZE: int = int(_config["buffer_size"])

# Reliable communication
RELIABLE_TIMEOUT: float = float(_config["reliable_timeout"])
RELIABLE_RETRIES: int = int(_config["reliable_retries"])
