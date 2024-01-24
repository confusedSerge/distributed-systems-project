import os
import logging

from constant import logger as con_log


def create_logger(name: str) -> logging.Logger:
    """Creates a logger with corresponding file.

    Args:
        name (str): The name of the logger and corresponding file.
    """
    path = con_log.LOGGING_PATH + name + ".log"

    if os.path.isdir("log") == False:
        os.mkdir("log")
    handler = logging.FileHandler(path)
    handler.setFormatter(logging.Formatter(con_log.LOGGING_FORMAT))

    logger = logging.getLogger(name)
    logger.setLevel(con_log.LOGGING_LEVEL)
    logger.addHandler(handler)

    return logger
