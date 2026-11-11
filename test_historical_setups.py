import sys
import io
import logging

# Ensure UTF-8 output encoding across Windows PowerShell and Linux
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Silence intermediate StrategyEngine INFO logs during backtest replay
logging.getLogger("StrategyEngine").setLevel(logging.WARNING)
logging.getLogger("DataIngestion").setLevel(logging.WARNING)

import asyncio
import pandas as pd
from src.data_ingestion import DataIngestion
from src.indicators import TechnicalIndicators
from src.strategy_engine import PullbackRejectionStrategy

def is_gold_weekend(dt) -> bool:
    """Check if a timestamp falls within the Gold weekend market closure (Sat 03:30 AM to Mon 04:30 AM IST)."""
    weekday = dt.weekday() # 0 = Monday, 5 = Saturday, 6 = Sunday
    t = dt.time()
    if weekday == 5 and t >= pd.to_datetime("03:30").time():
        return True
    if weekday == 6:
        return True
    if weekday == 0 and t < pd.to_datetime("04:30").time():
        return True
    return False

async def backtest_scan(symbol: str = "BTC/USDT", timeframe: str = "4h", limit: int = 1000):
    print("\n" + "=" * 115)
    print(f"📊 SNIPER 10/15 EMA RIBBON HISTORICAL SETUP SCANNER")
    print(f"Asset: {symbol} | Timeframe: {timeframe} | Scanning last {limit} candles...")
    print("=" * 115)

    ingestion = DataIngestion()
    strategy = PullbackRejectionStrategy()

    df = await ingestion.fetch_ohlcv_dataframe(symbol, timeframe, limit)
    if df is None or df.empty:
        print(f"❌ Failed to fetch market data for {symbol}.")
        return

    # Filter out weekend closure bars for Gold
    if symbol in ["XAU/USD", "GOLD"]:
        initial_count = len(df)
        df = df[~df["timestamp"].apply(is_gold_weekend)].reset_index(drop=True)
        filtered_count = initial_count - len(df)
        if filtered_count > 0:
            print(f"ℹ️ Filtered out {filtered_count} weekend closed-market bars (Sat 3:30 AM - Mon 4:30 AM IST).")

    # Calculate indicators over the historical dataframe
    df = TechnicalIndicators.calculate_emas(df, fast_period=10, mid_period=15, slow_period=200)

    detected_setups = []

    # Replay bar by bar historically (starting from candle 205 to allow EMA_200 warm-up)
    for i in range(205, len(df)):
        sub_df = df.iloc[:i+1].copy()
        
        is_bearish, bear_pattern, bear_sl = strategy.evaluate_bearish_setup(sub_df)
        is_bullish, bull_pattern, bull_sl = strategy.evaluate_bullish_setup(sub_df)

        if is_bearish or is_bullish:
            candle = sub_df.iloc[-2] # Rejection / Signal candle (just closed)
            entry_price = candle["close"]
            
            if is_bearish:
                signal_type = "🚨 BEARISH"
                pattern = bear_pattern
            else:
                signal_type = "🟢 BULLISH"
                pattern = bull_pattern

            detected_setups.append({
                "Timestamp (IST)": candle["timestamp"].strftime("%d-%m-%Y %I:%M %p"),
                "Asset": symbol,
                "Type": signal_type,
                "Pattern": pattern,
                "Entry": f"${entry_price:,.2f}"
            })

    if not detected_setups:
        print(f"\nℹ️ No sniper setups occurred for {symbol} on {timeframe} in the scanned {limit} candles.\n")
    else:
        print(f"\n🎯 FOUND {len(detected_setups)} SNIPER SETUP(S) FOR {symbol} ({timeframe}):\n")
        results_df = pd.DataFrame(detected_setups)
        # Configure pandas display width so the single table does not wrap awkwardly
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', 1000)
        pd.set_option('display.max_rows', None)
        print(results_df.to_string(index=False))
        print("\n" + "=" * 115)
        print("💡 TIP: Match the 'Timestamp (IST)' above to your TradingView chart to inspect entry candles!")
        print("=" * 115 + "\n")

if __name__ == "__main__":
    tf = sys.argv[1] if len(sys.argv) > 1 else "4h"
    sym = sys.argv[2] if len(sys.argv) > 2 else "BTC/USDT"
    lim = int(sys.argv[3]) if len(sys.argv) > 3 else (1500 if tf == "15m" else 500)
    asyncio.run(backtest_scan(symbol=sym, timeframe=tf, limit=lim))

