"""Centralized configuration system using Pydantic Settings.

Supports loading from environment variables, .env file, and safe defaults.
Defaults to PAPER TRADING mode with strict risk safeguards.
"""

from typing import List, Optional
import os
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "trading_ai/.env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Application
    APP_NAME: str = "Trading AI Platform"
    APP_VERSION: str = "2.0.0"
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    DEBUG: bool = False
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Trading Execution Mode: "paper" or "live"
    TRADING_MODE: str = Field(default="paper", description="Operating mode: paper or live")
    SAFE_KILL_SWITCH_ACTIVE: bool = Field(default=False, description="Emergency kill switch to halt all trading")
    INITIAL_PAPER_BALANCE: float = Field(default=10000.0, description="Virtual initial balance for paper trading")

    # Binance Credentials (OPTIONAL for paper trading)
    BINANCE_API_KEY: str = Field(default="", description="Binance API Key")
    BINANCE_API_SECRET: str = Field(default="", description="Binance API Secret")
    BINANCE_TESTNET: bool = Field(default=True, description="Whether to use Binance Futures Testnet")

    # Telegram Alerting (Optional)
    TELEGRAM_BOT_TOKEN: str = Field(default="", description="Telegram Bot Token")
    TELEGRAM_CHAT_ID: str = Field(default="", description="Telegram Chat ID")
    TELEGRAM_ENABLED: bool = Field(default=False, description="Enable telegram alerts")

    # Persistence
    DATABASE_URL: str = Field(default="sqlite:///./trading_ai.db", description="SQLAlchemy database URL")

    # Risk Management Constraints
    MAX_RISK_PER_TRADE: float = Field(default=0.01, description="Fraction of equity at risk per trade (e.g. 0.01 = 1%)")
    DEFAULT_LEVERAGE: int = Field(default=3, description="Default leverage for futures trading")
    MAX_DAILY_LOSS_PCT: float = Field(default=0.02, description="Daily loss limit threshold (e.g. 0.02 = 2%)")
    MAX_DRAWDOWN_PCT: float = Field(default=0.10, description="Trailing drawdown limit threshold (e.g. 0.10 = 10%)")
    MAX_CONSECUTIVE_LOSSES: int = Field(default=3, description="Circuit breaker after N consecutive losses")
    COOLDOWN_MINUTES: int = Field(default=15, description="Cooldown duration after loss/circuit breaker")
    MAX_OPEN_POSITIONS: int = Field(default=3, description="Max concurrent open positions")

    # Strategy & Machine Learning Defaults
    DEFAULT_SYMBOLS_STR: str = "BTCUSDT,ETHUSDT,BNBUSDT,SOLUSDT"
    ENTRY_TIMEFRAME: str = "5m"
    DIRECTION_TIMEFRAME: str = "1h"
    REGIME_TIMEFRAME: str = "4h"
    ML_EDGE_THRESHOLD: float = 0.12
    ML_MIN_PROBABILITY: float = 0.45

    @property
    def cors_origin_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def default_symbols(self) -> List[str]:
        return [sym.strip() for sym in self.DEFAULT_SYMBOLS_STR.split(",") if sym.strip()]

    @property
    def is_paper_trading(self) -> bool:
        return self.TRADING_MODE.lower().strip() != "live"


# Fallback for environments where pydantic-settings may not be installed yet
try:
    settings = Settings()
except Exception:
    class BasicSettings:
        APP_NAME = "Trading AI Platform"
        APP_VERSION = "2.0.0"
        HOST = "127.0.0.1"
        PORT = 8000
        DEBUG = False
        TRADING_MODE = os.getenv("TRADING_MODE", "paper")
        SAFE_KILL_SWITCH_ACTIVE = os.getenv("SAFE_KILL_SWITCH_ACTIVE", "false").lower() == "true"
        INITIAL_PAPER_BALANCE = float(os.getenv("INITIAL_PAPER_BALANCE", 10000.0))
        BINANCE_API_KEY = os.getenv("BINANCE_API_KEY", "")
        BINANCE_API_SECRET = os.getenv("BINANCE_API_SECRET", "")
        BINANCE_TESTNET = os.getenv("BINANCE_TESTNET", "true").lower() == "true"
        TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
        TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
        TELEGRAM_ENABLED = os.getenv("TELEGRAM_ENABLED", "false").lower() == "true"
        DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./trading_ai.db")
        MAX_RISK_PER_TRADE = float(os.getenv("MAX_RISK_PER_TRADE", 0.01))
        DEFAULT_LEVERAGE = int(os.getenv("DEFAULT_LEVERAGE", 3))
        MAX_DAILY_LOSS_PCT = float(os.getenv("MAX_DAILY_LOSS_PCT", 0.02))
        MAX_DRAWDOWN_PCT = float(os.getenv("MAX_DRAWDOWN_PCT", 0.10))
        MAX_CONSECUTIVE_LOSSES = int(os.getenv("MAX_CONSECUTIVE_LOSSES", 3))
        COOLDOWN_MINUTES = int(os.getenv("COOLDOWN_MINUTES", 15))
        MAX_OPEN_POSITIONS = int(os.getenv("MAX_OPEN_POSITIONS", 3))
        ENTRY_TIMEFRAME = "5m"
        DIRECTION_TIMEFRAME = "1h"
        REGIME_TIMEFRAME = "4h"
        ML_EDGE_THRESHOLD = 0.12
        ML_MIN_PROBABILITY = 0.45
        cors_origin_list = ["http://localhost:5173", "http://127.0.0.1:5173"]
        default_symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT"]

        @property
        def is_paper_trading(self) -> bool:
            return self.TRADING_MODE.lower().strip() != "live"

    settings = BasicSettings()
