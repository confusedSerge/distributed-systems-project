import logging
import os

from constant import logger as constant_logger


def create_logger(name: str) -> logging.Logger:
    """Creates a logger with corresponding file.

    Args:
        name (str): The name of the logger and corresponding file.
    """
    path = constant_logger.LOGGING_PATH + name + ".log"

    if os.path.isdir("log") == False:
        os.mkdir("log")
    handler = logging.FileHandler(path)
    handler.setFormatter(logging.Formatter(constant_logger.LOGGING_FORMAT))

    logger = logging.getLogger(name)
    logger.setLevel(constant_logger.LOGGING_LEVEL)
    logger.addHandler(handler)

    return logger
