"""
logger.py — Centralized Application Logger
Logs to both terminal and app.log file.
Shows: time, level, file name, function name, message.
"""

import logging
import sys
from app.core.config import settings


def _build_logger() -> logging.Logger:
    logger = logging.getLogger("ask_docs")

    # Avoid duplicate logs when imported multiple times
    if logger.handlers:
        return logger

    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    logger.setLevel(level)

    formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(filename)s - %(funcName)s - %(message)s"
    )

    # Terminal logs
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File logs
    file_handler = logging.FileHandler("app.log", mode="a")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    logger.propagate = False #Do not send this logger upward to the root logger so it doesn't get logged twice.

    # Keep third-party logs quiet
    # logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    # logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)
    # logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

    return logger


logger = _build_logger()