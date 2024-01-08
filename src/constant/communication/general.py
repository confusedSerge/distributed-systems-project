from util.config import load_config

config = load_config()["communication"]

TIMEOUT: int = int(config["timeout"])
