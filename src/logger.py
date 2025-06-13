#!/usr/bin/env python3
# File: src.logger.py
import logging
import logging.config
import os
import traceback

from src.__config__ import LOG_DIR, log_config

# Flag to track if logging has been configured
_logging_configured = False


def getLogger(name: str = None, level: str = os.getenv("LOG_LEVEL", "DEBUG")):
    """Create and return a logger with the caller's base filename or a custom name."""
    global _logging_configured
    if not _logging_configured:
        # Create the log directory if it doesn't exist
        if not os.path.exists(LOG_DIR):
            os.makedirs(LOG_DIR, exist_ok=True)
            # print(f"Created log directory: {LOG_DIR}")
        # else:
        #     print(f"Log directory already exists: {LOG_DIR.split('/')[-1]}")
        # Configure logging once
        logging.config.dictConfig(log_config)
        _logging_configured = True

    # Use the caller's base filename if no name is provided
    if name is None:
        caller_filename = os.path.basename(get_calling_filename())
        name = caller_filename

    logger = logging.getLogger(name)
    logger.setLevel(level)
    return logger


def get_calling_filename():
    """Return the full filename of the caller."""
    stack = traceback.extract_stack()
    # The second-to-last frame is the caller of getLogger
    calling_frame = stack[-2]
    return calling_frame.filename


def reduce_log_dir(size: int, logger: logging.Logger):
    """Remove old log files if the directory exceeds the specified size."""
    log_dir = LOG_DIR
    if log_dir:
        logs = os.listdir(log_dir)
        if len(logs) > size:
            logs.sort()
            for i in range(len(logs) - size):
                log_file = os.path.join(log_dir, logs[i])
                os.remove(log_file)
                logger.debug(f"Removed log file: {log_file}")
    else:
        logger.debug("No log directory specified")


# Example usage
if __name__ == "__main__":
    log = getLogger()
    log.debug("Debug message")
    log.debug(f"Calling filename: {get_calling_filename()}")
    log.info("Info message")
    log.warning("Warning message")
    log.error("Error message")
    log.critical("Critical message")
    log.debug("Debug message")
