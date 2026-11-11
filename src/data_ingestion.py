import ccxt
import requests
import pandas as pd
import logging
import asyncio
from typing import Optional
from config.settings import TWELVE_DATA_API_KEY

logger = logging.getLogger("DataIngestion")

class DataIngestion:
    def __init__(self):
        # Synchronous ccxt client
        self.exchange = ccxt.binance({
            'enableRateLimit': True
        })

    def _convert_timeframe_for_twelvedata(self, timeframe: str) -> str:
        """Map standard timeframe format ('15m', '4h') to Twelve Data intervals."""
        tf = timeframe.lower()
        if tf.endswith("m"):
            return f"{tf[:-1]}min"
        if tf.endswith("h"):
            return tf
        if tf.endswith("d"):
            return f"{tf[:-1]}day"
        return "15min"

    def _fetch_twelvedata_sync(self, symbol: str, timeframe: str, limit: int) -> Optional[pd.DataFrame]:
        """Fetch historical candle series from Twelve Data REST API."""
        if not TWELVE_DATA_API_KEY:
            logger.warning(
                f"TWELVE_DATA_API_KEY is not configured in .env. "
                f"Falling back to Binance PAXG/USDT for {symbol} gold data..."
            )
            return None

        try:
            interval = self._convert_timeframe_for_twelvedata(timeframe)
            url = (
                f"https://api.twelvedata.com/time_series?"
                f"symbol={symbol}&interval={interval}&outputsize={limit}&apikey={TWELVE_DATA_API_KEY}&timezone=UTC"
            )
            resp = requests.get(url, timeout=15)
            data = resp.json()

            if data.get("status") != "ok" or "values" not in data:
                err_msg = data.get("message", "Unknown API error")
                logger.error(f"Twelve Data error for {symbol}: {err_msg}")
                return None

            values = data["values"]
            if not values:
                return None

            # Twelve Data returns latest candle first; reverse to match standard ascending OHLCV
            values.reverse()
            df = pd.DataFrame(values)

            # Convert UTC datetime to Indian Standard Time (IST / Asia/Kolkata)
            df['timestamp'] = pd.to_datetime(df['datetime'], utc=True).dt.tz_convert('Asia/Kolkata').dt.tz_localize(None)

            for col in ['open', 'high', 'low', 'close', 'volume']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
                else:
                    df[col] = 0.0

            return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
        except Exception as e:
            logger.error(f"Failed to fetch {symbol} from Twelve Data: {str(e)}")
            return None

    def _fetch_binance_sync(self, symbol: str, timeframe: str, limit: int) -> Optional[pd.DataFrame]:
        """Fetch OHLCV candles from Binance via CCXT."""
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            if not ohlcv:
                return None

            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            # Convert UTC timestamp to Indian Standard Time (IST / Asia/Kolkata)
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True).dt.tz_convert('Asia/Kolkata').dt.tz_localize(None)
            return df
        except Exception as e:
            logger.error(f"Failed to fetch {symbol} from Binance: {str(e)}")
            return None

    async def fetch_ohlcv_dataframe(
        self, 
        symbol: str, 
        timeframe: str, 
        limit: int, 
        source: Optional[str] = None
    ) -> Optional[pd.DataFrame]:
        """Async dispatcher to fetch candle series based on symbol and source."""
        # Check if symbol is Gold or explicitly set to Twelve Data
        is_twelvedata = (source == "twelvedata") or (symbol in ["XAU/USD", "GOLD"])

        if is_twelvedata:
            df = await asyncio.to_thread(self._fetch_twelvedata_sync, symbol, timeframe, limit)
            # If Twelve Data succeeded, return it
            if df is not None and not df.empty:
                return df
            # Fallback to PAXG/USDT on Binance if Twelve Data key not set or failed
            logger.info("Attempting Binance PAXG/USDT fallback for Gold tracking...")
            return await asyncio.to_thread(self._fetch_binance_sync, "PAXG/USDT", timeframe, limit)

        # Standard Binance crypto symbols
        return await asyncio.to_thread(self._fetch_binance_sync, symbol, timeframe, limit)

    async def close(self):
        pass
