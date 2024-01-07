import logging

from util.helper import load_config

config = load_config()["logger"]

# Logger
LOGGING_PATH: str = config["path"]
LOGGING_FORMAT: str = config["format"]

# Calculate the logging level from the string
LOGGING_LEVEL: int = logging.INFO
match config["level"]:
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
