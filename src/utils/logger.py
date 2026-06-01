"""Logging utility - file + console output."""

import logging
import os

from src.config import LOGS_DIR, PROJECT_ROOT

LOG_FILE = LOGS_DIR / "pipeline.log"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - [%(funcName)s] %(message)s"

def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    formatter = logging.Formatter(LOG_FORMAT)

    os.makedirs(LOGS_DIR, exist_ok=True)

    fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
    fh.setLevel(logging.INFO)
    fh.setFormatter(formatter)

    sh = logging.StreamHandler()
    sh.setLevel(logging.INFO)
    sh.setFormatter(formatter)

    logger.addHandler(fh)
    logger.addHandler(sh)
    return logger