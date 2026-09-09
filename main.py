import asyncio
import logging
from config.settings import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from src.data_ingestion import DataIngestion
from src.indicators import TechnicalIndicators
from src.strategy_engine import PullbackRejectionStrategy
from src.alerts import TelegramAlertManager

logger = logging.getLogger("MainOrchestrator")

async def run_scanner():
    logger.info("Initializing Quant Scanner Runtime Systems...")
    
    ingestion = DataIngestion()
    strategy = PullbackRejectionStrategy()
    alerter = TelegramAlertManager(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)
    
    # Configuration explicitly defined for the async loop
    btc_cfg = {
        "symbol": "BTC/USDT",
        "timeframe": "15m",
        "fast_ema": 10,
        "slow_ema": 200,
        "limit": 250
    }

    
    print(f"DEBUG: Active Timeframe is {btc_cfg['timeframe']}")
    last_processed_timestamp = None

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
                    logger.info(f"New data fetched. Latest closed candle (IST): {formatted_ist_time} | Close Price: ${current_close_price}")
                    
                    # Compute indicators
                    df = TechnicalIndicators.calculate_emas(df, btc_cfg["fast_ema"], btc_cfg["slow_ema"])
                    
                    # Evaluate trading logic
                    is_bearish = strategy.evaluate_bearish_setup(df)
                    is_bullish = strategy.evaluate_bullish_setup(df)
                    
                    if is_bearish:
                        logger.warning("🚨 BEARISH PULLBACK REJECTION DETECTED 🚨")
                        alert_msg = (
                            f"🚨 <b>STRATEGY ALERT: BEARISH CONTINUATION</b> 🚨\n\n"
                            f"• <b>Asset:</b> <code>{btc_cfg['symbol']}</code>\n"
                            f"• <b>Timeframe:</b> <code>{btc_cfg['timeframe']}</code>\n"
                            f"• <b>Time (IST):</b> <code>{formatted_ist_time}</code>\n"
                            f"• <b>Setup Status:</b> Bearish Rejection Confirmed\n"
                            f"• <b>Execution Candle Close:</b> <code>${current_close_price}</code>\n"
                        )
                        await alerter.send_alert(alert_msg)
                    elif is_bullish:
                        logger.warning("🟢 BULLISH PULLBACK REJECTION DETECTED 🟢")
                        alert_msg = (
                            f"🟢 <b>STRATEGY ALERT: BULLISH CONTINUATION</b> 🟢\n\n"
                            f"• <b>Asset:</b> <code>{btc_cfg['symbol']}</code>\n"
                            f"• <b>Timeframe:</b> <code>{btc_cfg['timeframe']}</code>\n"
                            f"• <b>Time (IST):</b> <code>{formatted_ist_time}</code>\n"
                            f"• <b>Setup Status:</b> Bullish Pullback Rejection Confirmed\n"
                            f"• <b>Execution Candle Close:</b> <code>${current_close_price}</code>\n"
                        )
                        await alerter.send_alert(alert_msg)
                    else:
                        logger.info("Market data evaluated: No valid setup found on this candle.")
                    
                    last_processed_timestamp = current_closed_candle_time
                else:
                    logger.info("Candle is still active. Skipping logic evaluation to avoid lookahead/repainting bias.")
            else:
                logger.warning("Network connected, but returned an empty dataframe.")
            
            # Wait 60 seconds before polling Binance again
            await asyncio.sleep(60)
            
        except Exception as e:
            logger.error(f"Main Loop failed with error: {str(e)}")
            await asyncio.sleep(15)

if __name__ == "__main__":
    import sys, io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', line_buffering=True)
    try:
        asyncio.run(run_scanner())
    except KeyboardInterrupt:
        logger.info("System gracefully terminated by Operator.")