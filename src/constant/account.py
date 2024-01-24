from util.config import load_config

_config = load_config()["account"]

USERNAME: str = _config["username"]
