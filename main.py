import asyncio
import logging
import time
from datetime import datetime, timedelta, timezone

from config.settings import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, ACTIVE_ASSETS
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

def check_forex_weekend(now_ist: datetime) -> tuple[bool, float]:
    """
    Check if current IST time falls in the Gold/Forex weekend closure:
    Closes: Saturday 03:30 AM IST | Reopens: Monday 04:30 AM IST
    Returns: (is_closed, seconds_until_reopen)
    """
    weekday = now_ist.weekday()  # Monday is 0, Saturday is 5, Sunday is 6
    t = now_ist.time()
    
    # Saturday after 03:30 AM IST
    if weekday == 5 and t >= datetime.strptime("03:30", "%H:%M").time():
        days_ahead = 2
        reopen = now_ist.replace(hour=4, minute=30, second=0, microsecond=0) + timedelta(days=days_ahead)
        return True, (reopen - now_ist).total_seconds()
        
    # Entire Sunday
    if weekday == 6:
        days_ahead = 1
        reopen = now_ist.replace(hour=4, minute=30, second=0, microsecond=0) + timedelta(days=days_ahead)
        return True, (reopen - now_ist).total_seconds()
        
    # Monday before 04:30 AM IST
    if weekday == 0 and t < datetime.strptime("04:30", "%H:%M").time():
        reopen = now_ist.replace(hour=4, minute=30, second=0, microsecond=0)
        return True, (reopen - now_ist).total_seconds()
        
    return False, 0.0

async def scan_asset_loop(
    cfg: dict, 
    ingestion: DataIngestion, 
    strategy: PullbackRejectionStrategy, 
    alerter: TelegramAlertManager
):
    """Autonomous scanning loop for a single asset with independent timeframe synchronization."""
    symbol = cfg["symbol"]
    timeframe = cfg["timeframe"]
    limit = cfg.get("limit", 250)
    fast_ema = cfg.get("fast_ema", 10)
    mid_ema = cfg.get("mid_ema", 15)
    slow_ema = cfg.get("slow_ema", 200)
    source = cfg.get("source", "binance")

    logger.info(f"[{symbol}] Worker initialized (Timeframe: {timeframe} | Source: {source})")
    last_processed_timestamp = None

    while True:
        try:
            # Check for Gold / Forex weekend market closure (Sat 03:30 AM to Mon 04:30 AM IST)
            if symbol in ["XAU/USD", "GOLD"]:
                ist_offset = timezone(timedelta(hours=5, minutes=30))
                now_ist = datetime.now(ist_offset)
                is_closed, sleep_secs = check_forex_weekend(now_ist)
                if is_closed:
                    hours_left = sleep_secs / 3600.0
                    logger.info(
                        f"[{symbol}] Weekend market closure active (Sat 03:30 AM - Mon 04:30 AM IST). "
                        f"Pausing Gold worker for {hours_left:.1f} hours until market reopens..."
                    )
                    await asyncio.sleep(sleep_secs)
                    continue

            logger.info(f"[{symbol}] Scanning market cycle ({timeframe})...")
            
            # 1. Fetch live market data (Binance or Twelve Data)
            df = await ingestion.fetch_ohlcv_dataframe(
                symbol=symbol, 
                timeframe=timeframe, 
                limit=limit,
                source=source
            )
            
            if df is not None and not df.empty:
                current_closed_candle_time = df.iloc[-2]['timestamp']
                current_close_price = df.iloc[-2]['close']
                
                # 2. Process Strategy Logic upon new closed bar
                if last_processed_timestamp != current_closed_candle_time:
                    formatted_ist_time = current_closed_candle_time.strftime("%d-%m-%Y %I:%M:%S %p")
                    logger.info(f"[{symbol}] New closed candle (IST): {formatted_ist_time} | Close: ${current_close_price:,.2f}")
                    
                    # Compute indicators
                    df = TechnicalIndicators.calculate_emas(
                        df, 
                        fast_period=fast_ema, 
                        mid_period=mid_ema, 
                        slow_period=slow_ema
                    )
                    
                    # Evaluate trading logic
                    is_bearish, bear_pattern, bear_sl = strategy.evaluate_bearish_setup(df)
                    is_bullish, bull_pattern, bull_sl = strategy.evaluate_bullish_setup(df)
                    
                    c_reject = df.iloc[-2]
                    if is_bearish:
                        logger.warning(f"[{symbol}] 🚨 BEARISH {bear_pattern.upper()} DETECTED 🚨")
                        sl = bear_sl
                        risk = sl - current_close_price
                        risk_pct = (risk / current_close_price) * 100
                        target_1_5r = current_close_price - (risk * 1.5)
                        target_2r = current_close_price - (risk * 2.0)
                        
                        alert_msg = (
                            f"🎯 <b>SNIPER ALERT: BEARISH {bear_pattern.upper()}</b> 🎯\n\n"
                            f"• <b>Asset:</b> <code>{symbol}</code>\n"
                            f"• <b>Timeframe:</b> <code>{timeframe}</code>\n"
                            f"• <b>Pattern:</b> <code>{bear_pattern}</code>\n"
                            f"• <b>Time (IST):</b> <code>{formatted_ist_time}</code>\n"
                            f"• <b>Entry Price:</b> <code>${current_close_price:,.2f}</code>\n"
                            f"• <b>Stop Loss:</b> <code>${sl:,.2f}</code> ({risk_pct:.2f}% risk)\n"
                            f"• <b>Target 1 (1.5R):</b> <code>${target_1_5r:,.2f}</code>\n"
                            f"• <b>Target 2 (2.0R):</b> <code>${target_2r:,.2f}</code>\n"
                            f"• <b>EMA 10:</b> <code>${c_reject['EMA_10']:,.2f}</code> | <b>EMA 15:</b> <code>${c_reject['EMA_15']:,.2f}</code> | <b>EMA 200:</b> <code>${c_reject['EMA_200']:,.2f}</code>\n"
                        )
                        await alerter.send_alert(alert_msg)
                    elif is_bullish:
                        logger.warning(f"[{symbol}] 🟢 BULLISH {bull_pattern.upper()} DETECTED 🟢")
                        sl = bull_sl
                        risk = current_close_price - sl
                        risk_pct = (risk / current_close_price) * 100
                        target_1_5r = current_close_price + (risk * 1.5)
                        target_2r = current_close_price + (risk * 2.0)
                        
                        alert_msg = (
                            f"🎯 <b>SNIPER ALERT: BULLISH {bull_pattern.upper()}</b> 🎯\n\n"
                            f"• <b>Asset:</b> <code>{symbol}</code>\n"
                            f"• <b>Timeframe:</b> <code>{timeframe}</code>\n"
                            f"• <b>Pattern:</b> <code>{bull_pattern}</code>\n"
                            f"• <b>Time (IST):</b> <code>{formatted_ist_time}</code>\n"
                            f"• <b>Entry Price:</b> <code>${current_close_price:,.2f}</code>\n"
                            f"• <b>Stop Loss:</b> <code>${sl:,.2f}</code> ({risk_pct:.2f}% risk)\n"
                            f"• <b>Target 1 (1.5R):</b> <code>${target_1_5r:,.2f}</code>\n"
                            f"• <b>Target 2 (2.0R):</b> <code>${target_2r:,.2f}</code>\n"
                            f"• <b>EMA 10:</b> <code>${c_reject['EMA_10']:,.2f}</code> | <b>EMA 15:</b> <code>${c_reject['EMA_15']:,.2f}</code> | <b>EMA 200:</b> <code>${c_reject['EMA_200']:,.2f}</code>\n"
                        )
                        await alerter.send_alert(alert_msg)
                    else:
                        logger.info(f"[{symbol}] Market evaluated: No valid setup on this candle.")
                    
                    last_processed_timestamp = current_closed_candle_time
                    
                    # Independent Smart Sleep for this specific timeframe (+3s buffer)
                    sleep_seconds = get_seconds_until_candle_close(timeframe, buffer_seconds=3.0)
                    ist_offset = timezone(timedelta(hours=5, minutes=30))
                    next_wake_ist = (datetime.now(ist_offset) + timedelta(seconds=sleep_seconds)).strftime("%I:%M:%S %p")
                    logger.info(f"[{symbol}] Sleeping {int(sleep_seconds)}s until next {timeframe} candle close (~{next_wake_ist} IST)...")
                    await asyncio.sleep(sleep_seconds)
                else:
                    logger.info(f"[{symbol}] Candle not yet finalized on exchange. Retrying in 5 seconds...")
                    await asyncio.sleep(5)
            else:
                logger.warning(f"[{symbol}] Network connected, but returned empty data. Retrying in 15 seconds...")
                await asyncio.sleep(15)
                
        except (asyncio.CancelledError, KeyboardInterrupt):
            raise
        except Exception as e:
            logger.error(f"[{symbol}] Error in scanner loop: {str(e)}")
            await asyncio.sleep(15)

async def run_scanner():
    logger.info("Initializing Quant Scanner Multi-Asset Runtime...")
    
    ingestion = DataIngestion()
    strategy = PullbackRejectionStrategy()
    alerter = TelegramAlertManager(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)
    
    assets_summary = "\n".join([
        f"• <b>Asset:</b> <code>{a['symbol']}</code> ({a['timeframe']}) | Source: {a.get('source', 'binance')}"
        for a in ACTIVE_ASSETS
    ])
    
    # Send Startup Telegram Broadcast
    startup_msg = (
        f"🚀 <b>QUANT SCANNER ONLINE (MULTI-ASSET RUNTIME)</b> 🚀\n\n"
        f"{assets_summary}\n\n"
        f"• <b>Strategy:</b> Sniper 10/15 EMA Ribbon\n"
        f"• <b>Mode:</b> Async Multi-Timeframe Concurrent Engine\n"
        f"• <b>Status:</b> All asset workers active 24/7."
    )
    await alerter.send_alert(startup_msg)

    # Launch concurrent async workers for all configured assets
    tasks = [
        asyncio.create_task(scan_asset_loop(cfg, ingestion, strategy, alerter))
        for cfg in ACTIVE_ASSETS
    ]

    try:
        await asyncio.gather(*tasks)
    except (asyncio.CancelledError, KeyboardInterrupt):
        logger.info("Scanner shutdown signal received.")
    finally:
        termination_msg = (
            f"🛑 <b>QUANT SCANNER TERMINATED</b> 🛑\n\n"
            f"• <b>Status:</b> Multi-asset scanner workers offline."
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
