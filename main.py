import asyncio
import logging
import time
from datetime import datetime, timedelta, timezone

from config.settings import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from src.data_ingestion import DataIngestion
from src.indicators import TechnicalIndicators
from src.strategy_engine import PullbackRejectionStrategy
from src.alerts import TelegramAlertManager

logger = logging.getLogger("MainOrchestrator")

def timeframe_to_seconds(timeframe: str) -> int:
    """Convert timeframe string like '15m', '1h', '1d' into total seconds."""
    unit = timeframe[-1].lower()
    val = int(timeframe[:-1])
    multipliers = {
        's': 1,
        'm': 60,
        'h': 3600,
        'd': 86400,
        'w': 604800
    }
    return val * multipliers.get(unit, 60)

def get_seconds_until_candle_close(timeframe: str, buffer_seconds: float = 3.0) -> float:
    """Calculate exact seconds remaining until current candle close plus a network buffer."""
    tf_seconds = timeframe_to_seconds(timeframe)
    now = time.time()
    next_close = ((int(now) // tf_seconds) + 1) * tf_seconds
    seconds_remaining = (next_close - now) + buffer_seconds
    return max(seconds_remaining, buffer_seconds)

async def run_scanner():
    logger.info("Initializing Quant Scanner Runtime Systems...")
    
    ingestion = DataIngestion()
    strategy = PullbackRejectionStrategy()
    alerter = TelegramAlertManager(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)
    
    # Configuration explicitly defined for the async loop
    btc_cfg = {
        "symbol": "BTC/USDT",
        "timeframe": "4h",
        "fast_ema": 10,
        "slow_ema": 200,
        "limit": 250
    }

    print(f"DEBUG: Active Timeframe is {btc_cfg['timeframe']}")
    last_processed_timestamp = None

    # Send Startup Telegram Alert
    startup_msg = (
        f"🚀 <b>QUANT SCANNER ONLINE</b> 🚀\n\n"
        f"• <b>Asset:</b> <code>{btc_cfg['symbol']}</code>\n"
        f"• <b>Timeframe:</b> <code>{btc_cfg['timeframe']}</code>\n"
        f"• <b>EMAs:</b> Fast {btc_cfg['fast_ema']} | Slow {btc_cfg['slow_ema']}\n"
        f"• <b>Polling Mode:</b> Smart Sleep (Candle-Synchronized)\n"
        f"• <b>Status:</b> Scanner is running and monitoring candles."
    )
    await alerter.send_alert(startup_msg)

    try:
        while True:
            try:
                logger.info(f"Scanning market cycle for asset: {btc_cfg['symbol']}...")
                
                # 1. Fetch live market data
                df = await ingestion.fetch_ohlcv_dataframe(
                    symbol=btc_cfg["symbol"], 
                    timeframe=btc_cfg["timeframe"], 
                    limit=btc_cfg["limit"]
                )
                
                if df is not None and not df.empty:
                    current_closed_candle_time = df.iloc[-2]['timestamp']
                    current_close_price = df.iloc[-2]['close']
                    
                    # 2. Process Strategy Logic
                    if last_processed_timestamp != current_closed_candle_time:
                        formatted_ist_time = current_closed_candle_time.strftime("%d-%m-%Y %I:%M:%S %p")
                        logger.info(f"New closed candle finalized (IST): {formatted_ist_time} | Close Price: ${current_close_price}")
                        
                        # Compute indicators
                        df = TechnicalIndicators.calculate_emas(df, btc_cfg["fast_ema"], btc_cfg["slow_ema"])
                        
                        # Evaluate trading logic
                        is_bearish = strategy.evaluate_bearish_setup(df)
                        is_bullish = strategy.evaluate_bullish_setup(df)
                        
                        c_reject = df.iloc[-2]
                        if is_bearish:
                            logger.warning("🚨 BEARISH PULLBACK REJECTION DETECTED 🚨")
                            sl = c_reject["high"]
                            risk = sl - current_close_price
                            risk_pct = (risk / current_close_price) * 100
                            target_1_5r = current_close_price - (risk * 1.5)
                            target_2r = current_close_price - (risk * 2.0)
                            
                            alert_msg = (
                                f"🎯 <b>SNIPER ALERT: BEARISH REJECTION</b> 🎯\n\n"
                                f"• <b>Asset:</b> <code>{btc_cfg['symbol']}</code>\n"
                                f"• <b>Timeframe:</b> <code>{btc_cfg['timeframe']}</code>\n"
                                f"• <b>Time (IST):</b> <code>{formatted_ist_time}</code>\n"
                                f"• <b>Entry Price:</b> <code>${current_close_price:,.2f}</code>\n"
                                f"• <b>Stop Loss:</b> <code>${sl:,.2f}</code> ({risk_pct:.2f}% risk)\n"
                                f"• <b>Target 1 (1.5R):</b> <code>${target_1_5r:,.2f}</code>\n"
                                f"• <b>Target 2 (2.0R):</b> <code>${target_2r:,.2f}</code>\n"
                                f"• <b>EMA 10:</b> <code>${c_reject['EMA_10']:,.2f}</code> | <b>EMA 200:</b> <code>${c_reject['EMA_200']:,.2f}</code>\n"
                            )
                            await alerter.send_alert(alert_msg)
                        elif is_bullish:
                            logger.warning("🟢 BULLISH PULLBACK REJECTION DETECTED 🟢")
                            sl = c_reject["low"]
                            risk = current_close_price - sl
                            risk_pct = (risk / current_close_price) * 100
                            target_1_5r = current_close_price + (risk * 1.5)
                            target_2r = current_close_price + (risk * 2.0)
                            
                            alert_msg = (
                                f"🎯 <b>SNIPER ALERT: BULLISH REJECTION</b> 🎯\n\n"
                                f"• <b>Asset:</b> <code>{btc_cfg['symbol']}</code>\n"
                                f"• <b>Timeframe:</b> <code>{btc_cfg['timeframe']}</code>\n"
                                f"• <b>Time (IST):</b> <code>{formatted_ist_time}</code>\n"
                                f"• <b>Entry Price:</b> <code>${current_close_price:,.2f}</code>\n"
                                f"• <b>Stop Loss:</b> <code>${sl:,.2f}</code> ({risk_pct:.2f}% risk)\n"
                                f"• <b>Target 1 (1.5R):</b> <code>${target_1_5r:,.2f}</code>\n"
                                f"• <b>Target 2 (2.0R):</b> <code>${target_2r:,.2f}</code>\n"
                                f"• <b>EMA 10:</b> <code>${c_reject['EMA_10']:,.2f}</code> | <b>EMA 200:</b> <code>${c_reject['EMA_200']:,.2f}</code>\n"
                            )
                            await alerter.send_alert(alert_msg)
                        else:
                            logger.info("Market data evaluated: No valid setup found on this candle.")
                        
                        last_processed_timestamp = current_closed_candle_time
                        
                        # Calculate Smart Sleep until next candle close (+3s network buffer)
                        sleep_seconds = get_seconds_until_candle_close(btc_cfg["timeframe"], buffer_seconds=3.0)
                        ist_offset = timezone(timedelta(hours=5, minutes=30))
                        next_wake_ist = (datetime.now(ist_offset) + timedelta(seconds=sleep_seconds)).strftime("%I:%M:%S %p")
                        logger.info(f"Smart Sleep active: sleeping {int(sleep_seconds)}s until next candle close (~{next_wake_ist} IST)...")
                        await asyncio.sleep(sleep_seconds)
                    else:
                        # Rare case: exchange hasn't published the candle yet on boundary wakeup
                        logger.info("Candle not yet finalized on exchange. Retrying in 5 seconds...")
                        await asyncio.sleep(5)
                else:
                    logger.warning("Network connected, but returned an empty dataframe. Retrying in 15 seconds...")
                    await asyncio.sleep(15)
                
            except (asyncio.CancelledError, KeyboardInterrupt):
                raise
            except Exception as e:
                logger.error(f"Main Loop failed with error: {str(e)}")
                await asyncio.sleep(15)
    except (asyncio.CancelledError, KeyboardInterrupt):
        logger.info("Scanner shutdown signal received.")
    finally:
        termination_msg = (
            f"🛑 <b>QUANT SCANNER TERMINATED</b> 🛑\n\n"
            f"• <b>Asset:</b> <code>{btc_cfg['symbol']}</code>\n"
            f"• <b>Timeframe:</b> <code>{btc_cfg['timeframe']}</code>\n"
            f"• <b>Status:</b> System offline / Scanner terminated."
        )
        alerter.send_alert_sync(termination_msg)

if __name__ == "__main__":
    import sys, io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', line_buffering=True)
    try:
        asyncio.run(run_scanner())
    except KeyboardInterrupt:
        logger.info("System gracefully terminated by Operator.")