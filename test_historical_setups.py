import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import asyncio
import pandas as pd
from src.data_ingestion import DataIngestion
from src.indicators import TechnicalIndicators
from src.strategy_engine import PullbackRejectionStrategy

async def backtest_scan(symbol: str = "BTC/USDT", timeframe: str = "4h", limit: int = 500):
    print("=" * 85)
    print(f"📊 SNIPER 10/15 EMA RIBBON HISTORICAL SETUP SCANNER")
    print(f"Asset: {symbol} | Timeframe: {timeframe} | Scanning last {limit} candles...")
    print("=" * 85)

    ingestion = DataIngestion()
    strategy = PullbackRejectionStrategy()

    df = await ingestion.fetch_ohlcv_dataframe(symbol, timeframe, limit)
    if df is None or df.empty:
        print("❌ Failed to fetch market data.")
        return

    # Calculate indicators over the entire historical dataframe
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
                stop_loss = bear_sl
                risk = stop_loss - entry_price
                risk_pct = (risk / entry_price) * 100
                target_1_5r = entry_price - (risk * 1.5)
                target_2r = entry_price - (risk * 2.0)
            else:
                signal_type = "🟢 BULLISH"
                pattern = bull_pattern
                stop_loss = bull_sl
                risk = entry_price - stop_loss
                risk_pct = (risk / entry_price) * 100
                target_1_5r = entry_price + (risk * 1.5)
                target_2r = entry_price + (risk * 2.0)

            detected_setups.append({
                "Timestamp (IST)": candle["timestamp"].strftime("%d-%m-%Y %I:%M %p"),
                "Type": signal_type,
                "Pattern": pattern,
                "Entry Price": f"${entry_price:.2f}",
                "Stop Loss": f"${stop_loss:.2f}",
                "Risk %": f"{risk_pct:.2f}%",
                "Target (1.5R)": f"${target_1_5r:.2f}",
                "Target (2.0R)": f"${target_2r:.2f}",
                "EMA_10": f"${candle['EMA_10']:.2f}",
                "EMA_15": f"${candle['EMA_15']:.2f}",
                "EMA_200": f"${candle['EMA_200']:.2f}",
                "Volume": f"{candle['volume']:.2f}"
            })

    if not detected_setups:
        print("\nℹ️ No setups occurred in the scanned window.")
    else:
        print(f"\n🎯 FOUND {len(detected_setups)} SNIPER 10/15 EMA SETUP(S):\n")
        results_df = pd.DataFrame(detected_setups)
        print(results_df.to_string(index=False))
        print("\n💡 TIP: Check the timestamps above on your TradingView chart to inspect the exact entry candles!")

if __name__ == "__main__":
    tf = sys.argv[1] if len(sys.argv) > 1 else "4h"
    sym = sys.argv[2] if len(sys.argv) > 2 else "BTC/USDT"
    asyncio.run(backtest_scan(symbol=sym, timeframe=tf, limit=500))
