from util.config import load_config

config = load_config()["communication"]["unicast"]

# Unicast Communication
PORT = config["port"]
