import tomllib
import logging

with open("./config/config.dev.toml", "rb") as f:
    config = tomllib.load(f)

# Logger
LOGGING_PATH: str = config["logger"]["path"]
LOGGING_FORMAT: str = config["logger"]["format"]

# Calculate the logging level from the string
LOGGING_LEVEL: int = logging.INFO
match config["logger"]["level"]:
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
