from regex import E
from util.config import load_config

_config = load_config()["communication"]["replica"]

TIMEOUT = int(_config["timeout"])

REPLICATION_PERIOD = int(_config["replication"]["period"])
REPLICATION_TIMEOUT = int(_config["replication"]["timeout"])

HEARTBEAT_PERIOD = int(_config["heartbeat"]["period"])

ELECTION_PORTS = [int(port) for port in _config["election"]["ports"]]
ELECTION_TIMEOUT = int(_config["election"]["timeout"])
