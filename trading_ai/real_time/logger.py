import logging
import os
from logging.handlers import RotatingFileHandler

# =========================
# PATH SETUP
# =========================

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))
    )
)

LOG_DIR = os.path.join(BASE_DIR, "logs")

if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

BOT_LOG_FILE = os.path.join(LOG_DIR, "bot.log")
ERROR_LOG_FILE = os.path.join(LOG_DIR, "error.log")
TRADE_LOG_FILE = os.path.join(LOG_DIR, "trades.log")

# =========================
# FORMATTER
# =========================

formatter = logging.Formatter(
    "%(asctime)s | %(levelname)s | %(message)s"
)

# =========================
# MAIN BOT LOGGER
# =========================

logger = logging.getLogger("FUTURES_BOT")
logger.setLevel(logging.INFO)
logger.propagate = False  # Prevent duplicate logs

# Prevent duplicate handlers if reloaded
if not logger.handlers:

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Bot file handler (5MB rotation)
    bot_file_handler = RotatingFileHandler(
        BOT_LOG_FILE,
        maxBytes=5 * 1024 * 1024,
        backupCount=3
    )
    bot_file_handler.setFormatter(formatter)
    logger.addHandler(bot_file_handler)

    # Error file handler (ERROR only)
    error_file_handler = RotatingFileHandler(
        ERROR_LOG_FILE,
        maxBytes=5 * 1024 * 1024,
        backupCount=3
    )
    error_file_handler.setLevel(logging.ERROR)
    error_file_handler.setFormatter(formatter)
    logger.addHandler(error_file_handler)

# =========================
# TRADE LOGGER (Separate)
# =========================

trade_logger = logging.getLogger("TRADES")
trade_logger.setLevel(logging.INFO)
trade_logger.propagate = False

if not trade_logger.handlers:

    trade_file_handler = RotatingFileHandler(
        TRADE_LOG_FILE,
        maxBytes=5 * 1024 * 1024,
        backupCount=3
    )
    trade_file_handler.setFormatter(formatter)
    trade_logger.addHandler(trade_file_handler)

# =========================
# HELPER FUNCTIONS
# =========================

def log_info(message):
    logger.info(message)

def log_warning(message):
    logger.warning(message)

def log_error(message):
    logger.error(message)

def log_trade(message):
    trade_logger.info(message)