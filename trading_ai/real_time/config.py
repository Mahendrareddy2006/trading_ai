from dotenv import load_dotenv
import os

load_dotenv()

API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

SYMBOLS = ["BTCUSDT", "ETHUSDT"]
INTERVAL = "1m"
BOT_ACTIVE = True
LAST_UPDATE_ID = None

RISK_PERCENT = 0.003      # 0.3% stop loss
REWARD_PERCENT = 0.006 
RISK_PERCENT_PER_TRADE = 0.01   # 1% risk per trade