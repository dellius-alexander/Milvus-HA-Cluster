#!/usr/bin/env python3
# File: __config__.py: Project configuration file
# --------------------------------------------------------------
import logging
import os
import time

import dotenv

log = logging.getLogger(__name__)
# --------------------------------------------------------------
# Load environment variables from .env file
# --------------------------------------------------------------
try:
    env = dotenv.find_dotenv(filename=".env", raise_error_if_not_found=True, usecwd=False)
    dotenv.load_dotenv(env, override=True)
except Exception as e:
    log.error(f"Error loading .env file: {e}")
    exit(".env file not found or error loading it.")

# --------------------------------------------------------------
# Define project environment
# --------------------------------------------------------------
LOG_DIR = os.path.join("/tmp/log", "milvus")
LOG_FILE = f'{LOG_DIR}/milvus_{time.strftime("%Y%m%d%H%M%S")}.log'

# --------------------------------------------------------------
# Define log colors
log_colors_config = {
    "RESET": "reset",
    "DEBUG": "cyan",
    "INFO": "green",
    "WARNING": "yellow",
    "ERROR": "red",
    "CRITICAL": "red",
}

# --------------------------------------------------------------
# Logging configuration
log_config = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "class": "logging.Formatter",
            "format": "[%(asctime)s][%(levelname)s][%(name)s][%(lineno)s]: %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
            "style": "%",
        },
        "colored": {
            "()": "colorlog.ColoredFormatter",
            "format": "%(log_color)s[%(asctime)s][%(levelname)s][%(name)s][%(lineno)s]: %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
            "log_colors": log_colors_config,
            "style": "%",
        },
    },
    "handlers": {
        "stream": {
            "class": "colorlog.StreamHandler",
            "level": "DEBUG",
            "formatter": "colored",
        },
        "file_handler": {
            "class": "logging.handlers.TimedRotatingFileHandler",
            "filename": f"{LOG_FILE}",
            "when": "midnight",
            "interval": 1,
            "backupCount": 2,
            "encoding": "utf-8",
            "delay": False,
            "utc": False,
            "level": "DEBUG",
            "formatter": "standard",
        },
    },
    "root": {
        "handlers": ["stream", "file_handler"],
        "level": "DEBUG",
    },
}

