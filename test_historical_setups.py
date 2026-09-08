import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import asyncio
import pandas as pd
from src.data_ingestion import DataIngestion
from src.indicators import TechnicalIndicators
from src.strategy_engine import PullbackRejectionStrategy

async def backtest_scan(symbol: str = "BTC/USDT:USDT", timeframe: str = "1m", limit: int = 500):
    print("=" * 70)
    print(f"📊 HISTORICAL SETUP SCANNER & CHART VERIFIER")
    print(f"Asset: {symbol} | Timeframe: {timeframe} | Scanning last {limit} candles...")
    print("=" * 70)

    ingestion = DataIngestion()
    strategy = PullbackRejectionStrategy()

    df = await ingestion.fetch_ohlcv_dataframe(symbol, timeframe, limit)
    if df is None or df.empty:
        print("❌ Failed to fetch market data.")
        return

    # Calculate indicators over the entire historical dataframe
    df = TechnicalIndicators.calculate_emas(df, fast_period=10, slow_period=200)

    detected_setups = []

    # Replay bar by bar historically (starting from candle 205 to allow EMA_200 warm-up)
    for i in range(205, len(df)):
        sub_df = df.iloc[:i+1].copy()
        
        is_bearish = strategy.evaluate_bearish_setup(sub_df)
        is_bullish = strategy.evaluate_bullish_setup(sub_df)

        if is_bearish or is_bullish:
            candle = sub_df.iloc[-2] # Trigger candle
            reject_candle = sub_df.iloc[-3] # Rejection candle
            
            signal_type = "🚨 BEARISH" if is_bearish else "🟢 BULLISH"
            detected_setups.append({
                "Type": signal_type,
                "Trigger Time (IST)": candle["timestamp"].strftime("%d-%m-%Y %I:%M:%S %p"),
                "Trigger Close Price": f"${candle['close']:.2f}",
                "Rejection High": f"${reject_candle['high']:.2f}",
                "Rejection Low": f"${reject_candle['low']:.2f}",
                "EMA_10": f"${reject_candle['EMA_10']:.2f}",
                "EMA_200": f"${reject_candle['EMA_200']:.2f}",
                "Volume": f"{candle['volume']:.2f}"
            })

    if not detected_setups:
        print("\nℹ️ No setups occurred in the scanned window. (Conditions are strict: trend + 40% wick + EMA touch + volume expansion).")
    else:
        print(f"\n🎯 FOUND {len(detected_setups)} VALID SETUP(S):\n")
        results_df = pd.DataFrame(detected_setups)
        print(results_df.to_string(index=False))
        print("\n💡 TIP: Open your TradingView chart and check the timestamps above to see the exact candles!")

if __name__ == "__main__":
    tf = sys.argv[1] if len(sys.argv) > 1 else "1m"
    sym = sys.argv[2] if len(sys.argv) > 2 else "BTC/USDT:USDT"
    asyncio.run(backtest_scan(symbol=sym, timeframe=tf, limit=500))
