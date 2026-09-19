import pandas as pd
import pandas_ta as ta

class TechnicalIndicators:
    @staticmethod
    def calculate_emas(df: pd.DataFrame, fast_period: int = 10, slow_period: int = 200) -> pd.DataFrame:
        """
        Applies EMA and volatility metrics securely over historical sets.
        Expects a DataFrame containing standard ['open', 'high', 'low', 'close', 'volume'] columns.
        """
        df = df.copy()
        
        # Ensure the columns are numeric before calculations
        df["open"] = pd.to_numeric(df["open"])
        df["high"] = pd.to_numeric(df["high"])
        df["low"] = pd.to_numeric(df["low"])
        df["close"] = pd.to_numeric(df["close"])
        df["volume"] = pd.to_numeric(df["volume"])
        
        # Vectorized EMA calculation
        df[f"EMA_{fast_period}"] = ta.ema(df["close"], length=fast_period)
        df[f"EMA_{slow_period}"] = ta.ema(df["close"], length=slow_period)
        
        # Calculate EMA Slopes over a 3-candle rolling window for trend validation
        df[f"EMA_{slow_period}_slope"] = df[f"EMA_{slow_period}"].diff(3)

        # Volatility / ATR calculation (14 period)
        atr = ta.atr(df["high"], df["low"], df["close"], length=14)
        if atr is not None:
            df["ATR"] = atr

        return df