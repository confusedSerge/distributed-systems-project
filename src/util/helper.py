import logging
import tomllib

from constant import logger as constant_logger


def create_logger(name: str) -> logging.Logger:
    """Creates a logger with corresponding file.

    Args:
        name (str): The name of the logger and corresponding file.
    """
    path = constant_logger.LOGGING_PATH + name + ".log"

    handler = logging.FileHandler(path)
    handler.setFormatter(logging.Formatter(constant_logger.LOGGING_FORMAT))

    logger = logging.getLogger(name)
    logger.setLevel(constant_logger.LOGGING_LEVEL)
    logger.addHandler(handler)

    return logger


def load_config(path: str = "./config/config.dev.toml") -> dict:
    """Loads the configuration from the config file.

    Args:
        path (str, optional): The path to the config file. Defaults to "config/config.toml".

    Returns:
        dict: The configuration as a dictionary.
    """
    with open(path, "rb") as f:
        config = tomllib.load(f)

    return config
