from util.config import load_config

_config = load_config()["communication"]["unicast"]

# Unicast Communication
PORT = _config["port"]
