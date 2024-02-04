import logging

from util.config import load_config

_config = load_config()["logger"]

# Logger
LOGGING_PATH: str = _config["path"]
LOGGING_FORMAT_NORMAL: str = _config["format"]
LOGGING_FORMAT_PID: str = _config["format_pid"]

# Calculate the logging level from the string
LOGGING_LEVEL: int = logging.INFO
match _config["level"]:
    case "DEBUG":
        LOGGING_LEVEL = logging.DEBUG
    case "INFO":
        LOGGING_LEVEL = logging.INFO
    case "WARNING":
        LOGGING_LEVEL = logging.WARNING
    case "ERROR":
        LOGGING_LEVEL = logging.ERROR
    case "CRITICAL":
        LOGGING_LEVEL = logging.CRITICAL
    case _:
        LOGGING_LEVEL = logging.INFO
