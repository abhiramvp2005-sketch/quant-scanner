import ccxt
import pandas as pd
import logging
import asyncio
from typing import Optional

logger = logging.getLogger("DataIngestion")

class DataIngestion:
    def __init__(self):
        # Using the synchronous ccxt library because it natively respects Windows WARP VPN adapters
        self.exchange = ccxt.binanceusdm({
            'enableRateLimit': True
        })

    async def fetch_ohlcv_dataframe(self, symbol: str, timeframe: str, limit: int) -> Optional[pd.DataFrame]:
        try:
            # Execute the synchronous network call in a background thread to maintain async architecture
            ohlcv = await asyncio.to_thread(
                self.exchange.fetch_ohlcv, symbol, timeframe, limit=limit
            )
            if not ohlcv:
                return None
            
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            # Convert UTC timestamp to Indian Standard Time (IST / Asia/Kolkata)
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True).dt.tz_convert('Asia/Kolkata').dt.tz_localize(None)
            return df
        except Exception as e:
            logger.error(f"Failed to fetch market metrics from Binance for {symbol}: {str(e)}")
            return None

    async def close(self):
        # Synchronous CCXT objects don't require an async cleanup, but we keep the method for main.py compatibility
        pass