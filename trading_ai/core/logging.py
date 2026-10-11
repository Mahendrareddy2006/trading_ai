"""Structured application logger for Trading AI Platform."""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

APP_LOG_FILE = os.path.join(LOG_DIR, "trading_ai.log")
ERROR_LOG_FILE = os.path.join(LOG_DIR, "error.log")
TRADE_LOG_FILE = os.path.join(LOG_DIR, "trades.log")

FORMATTER = logging.Formatter(
    "%(asctime)s | %(levelname)-7s | [%(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)


def get_logger(name: str = "TradingAI") -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        # Stream / Console Handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(FORMATTER)
        logger.addHandler(console_handler)

        # Rotating App File Handler (10 MB rotation, max 5 backups)
        app_file_handler = RotatingFileHandler(
            APP_LOG_FILE, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
        )
        app_file_handler.setFormatter(FORMATTER)
        logger.addHandler(app_file_handler)

        # Rotating Error File Handler
        error_file_handler = RotatingFileHandler(
            ERROR_LOG_FILE, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
        )
        error_file_handler.setLevel(logging.ERROR)
        error_file_handler.setFormatter(FORMATTER)
        logger.addHandler(error_file_handler)

    return logger


logger = get_logger("System")
trade_logger = logging.getLogger("Trades")
trade_logger.setLevel(logging.INFO)
if not trade_logger.handlers:
    trade_handler = RotatingFileHandler(TRADE_LOG_FILE, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8")
    trade_handler.setFormatter(FORMATTER)
    trade_logger.addHandler(trade_handler)
