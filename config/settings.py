import os
import logging
from dotenv import load_dotenv
load_dotenv()

# Logging Configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("quant_scanner.log", mode="a")
    ]
)

# Core Trading Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "YOUR_CHAT_ID_HERE")

SCAN_INTERVAL_SECONDS = 60  # Polling interval for state checking

CONFIG_MAP = {
    "BTCUSDT": {
        "symbol": "BTC/USDT:USDT",
        "timeframe": "15m",
        "fast_ema": 10,
        "slow_ema": 200,
        "limit": 250  # Ensure enough historical bars to warm up 200 EMA
    }
}