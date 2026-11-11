import os
import sys
import logging
from dotenv import load_dotenv
load_dotenv()

# Force UTF-8 encoding on Windows standard streams
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Logging Configuration with explicit UTF-8
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("quant_scanner.log", mode="a", encoding="utf-8")
    ]
)

# Core Trading Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "YOUR_CHAT_ID_HERE")
TWELVE_DATA_API_KEY = os.getenv("TWELVE_DATA_API_KEY", "")

SCAN_INTERVAL_SECONDS = 60  # Polling interval for state checking

# Active Multi-Asset Configurations
ACTIVE_ASSETS = [
    {
        "symbol": "ETH/USDT",
        "timeframe": "4h",
        "fast_ema": 10,
        "mid_ema": 15,
        "slow_ema": 200,
        "limit": 250,
        "source": "binance"
    },
    {
        "symbol": "XAU/USD",
        "timeframe": "15m",
        "fast_ema": 10,
        "mid_ema": 15,
        "slow_ema": 200,
        "limit": 250,
        "source": "twelvedata"
    }
]
