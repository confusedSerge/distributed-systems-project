import os
import logging

# === Custom Modules ===

from constant import logger as logger_constants


def create_logger(name: str, with_pid: bool = False) -> logging.Logger:
    """Creates a logger with corresponding log file.

    Args:
        name (str): The name of the logger and corresponding file.
    """
    path = logger_constants.LOGGING_PATH + name + ".log"

    if os.path.isdir("log") == False:
        os.mkdir("log")
    handler = logging.FileHandler(path)
    handler.setFormatter(
        logging.Formatter(
            logger_constants.LOGGING_FORMAT_NORMAL
            if not with_pid
            else logger_constants.LOGGING_FORMAT_PID
        )
    )

    logger = logging.getLogger(name)
    logger.setLevel(logger_constants.LOGGING_LEVEL)
    logger.addHandler(handler)

    return logger
