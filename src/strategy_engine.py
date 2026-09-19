import pandas as pd
import logging

logger = logging.getLogger("StrategyEngine")

class PullbackRejectionStrategy:
    def __init__(self, fast_ema_col: str = "EMA_10", slow_ema_col: str = "EMA_200", min_atr_factor: float = 0.4):
        self.fast_ema = fast_ema_col
        self.slow_ema = slow_ema_col
        self.min_atr_factor = min_atr_factor

    def evaluate_bearish_setup(self, df: pd.DataFrame) -> bool:
        """
        Sniper Bearish Pullback Rejection:
        Evaluates candle -2 directly as the rejection bar, firing immediately 
        upon its close without waiting for an extra expansion candle.
        """
        if len(df) < 20:
            return False

        # -1 = currently forming candle (ignored to avoid repainting)
        # -2 = candidate rejection candle (just closed)
        # -3 = previous candle
        c_reject = df.iloc[-2]
        c_prev = df.iloc[-3]

        # 1. Macro Trend Regime (Fast EMA below Slow EMA, Close below Slow EMA)
        macro_downtrend = (c_reject[self.fast_ema] < c_reject[self.slow_ema]) and (c_reject["close"] < c_reject[self.slow_ema])
        if not macro_downtrend:
            return False

        # 2. Structural Pullback: High tests/approaches Fast EMA zone (within 0.05%)
        pullback_tested_ema = c_reject["high"] >= (c_reject[self.fast_ema] * 0.9995)
        closed_below_ema = c_reject["close"] < c_reject[self.fast_ema]
        if not (pullback_tested_ema and closed_below_ema):
            return False

        # 3. Proximity / Stretch Check: Prevent late entries if price already dumped far from EMA
        atr_val = c_reject.get("ATR")
        max_dist = atr_val * 0.65 if (pd.notna(atr_val) and atr_val > 0) else (c_reject[self.fast_ema] * 0.006)
        if (c_reject[self.fast_ema] - c_reject["close"]) > max_dist:
            return False

        # 4. Candlestick Signatures on candle -2:
        candle_range = c_reject["high"] - c_reject["low"]
        if candle_range <= 0:
            return False

        # Minimum Displacement check: filter micro-range dojis in flat chop
        if pd.notna(atr_val) and atr_val > 0:
            if candle_range < (atr_val * self.min_atr_factor):
                return False

        real_body_high = max(c_reject["open"], c_reject["close"])
        upper_wick = c_reject["high"] - real_body_high
        lower_wick = min(c_reject["open"], c_reject["close"]) - c_reject["low"]

        # Upper rejection wick: upper wick is at least 35% of total range and dominant over lower wick
        has_pinbar_rejection = (upper_wick >= candle_range * 0.35) and (upper_wick > lower_wick)
        
        # Bearish engulfing off the EMA (must show upper rejection into EMA)
        is_bearish_engulfing = (
            (c_reject["close"] < c_reject["open"]) and 
            (c_reject["open"] >= c_prev["close"]) and 
            (c_reject["close"] <= c_prev["open"]) and
            (upper_wick >= candle_range * 0.15)
        )

        valid_candlestick = has_pinbar_rejection or is_bearish_engulfing
        if not valid_candlestick:
            return False

        # 5. Volume Filter: Pinbars require 60% of baseline volume (pullback liquidity), engulfing requires 85%
        vol_baseline = df["volume"].rolling(10).mean().iloc[-2]
        min_vol_factor = 0.60 if has_pinbar_rejection else 0.85
        volume_filter = c_reject["volume"] >= (vol_baseline * min_vol_factor)

        if valid_candlestick and volume_filter:
            logger.info("🎯 SNIPER SETUP: Bearish Rejection Confirmed on Candle Close.")
            return True

        return False

    def evaluate_bullish_setup(self, df: pd.DataFrame) -> bool:
        """
        Sniper Bullish Pullback Rejection:
        Evaluates candle -2 directly as the rejection bar, firing immediately 
        upon its close without waiting for an extra expansion candle.
        """
        if len(df) < 20:
            return False

        # -1 = currently forming candle (ignored)
        # -2 = candidate rejection candle (just closed)
        # -3 = previous candle
        c_reject = df.iloc[-2]
        c_prev = df.iloc[-3]

        # 1. Macro Trend Regime (Fast EMA above Slow EMA, Close above Slow EMA)
        macro_uptrend = (c_reject[self.fast_ema] > c_reject[self.slow_ema]) and (c_reject["close"] > c_reject[self.slow_ema])
        if not macro_uptrend:
            return False

        # 2. Structural Pullback: Low tests/approaches Fast EMA zone (within 0.05%)
        pullback_tested_ema = c_reject["low"] <= (c_reject[self.fast_ema] * 1.0005)
        closed_above_ema = c_reject["close"] > c_reject[self.fast_ema]
        if not (pullback_tested_ema and closed_above_ema):
            return False

        # 3. Proximity / Stretch Check: Prevent late entries if price already expanded far above EMA
        atr_val = c_reject.get("ATR")
        max_dist = atr_val * 0.65 if (pd.notna(atr_val) and atr_val > 0) else (c_reject[self.fast_ema] * 0.006)
        if (c_reject["close"] - c_reject[self.fast_ema]) > max_dist:
            return False

        # 4. Candlestick Signatures on candle -2:
        candle_range = c_reject["high"] - c_reject["low"]
        if candle_range <= 0:
            return False

        # Minimum Displacement check: filter micro-range dojis in flat chop
        if pd.notna(atr_val) and atr_val > 0:
            if candle_range < (atr_val * self.min_atr_factor):
                return False

        real_body_low = min(c_reject["open"], c_reject["close"])
        lower_wick = real_body_low - c_reject["low"]
        upper_wick = c_reject["high"] - max(c_reject["open"], c_reject["close"])

        # Lower rejection wick: lower wick is at least 35% of total range and dominant over upper wick
        has_pinbar_rejection = (lower_wick >= candle_range * 0.35) and (lower_wick > upper_wick)
        
        # Bullish engulfing off the EMA (must show lower rejection into EMA)
        is_bullish_engulfing = (
            (c_reject["close"] > c_reject["open"]) and 
            (c_reject["open"] <= c_prev["close"]) and 
            (c_reject["close"] >= c_prev["open"]) and
            (lower_wick >= candle_range * 0.15)
        )

        valid_candlestick = has_pinbar_rejection or is_bullish_engulfing
        if not valid_candlestick:
            return False

        # 5. Volume Filter: Pinbars require 60% of baseline volume (pullback liquidity), engulfing requires 85%
        vol_baseline = df["volume"].rolling(10).mean().iloc[-2]
        min_vol_factor = 0.60 if has_pinbar_rejection else 0.85
        volume_filter = c_reject["volume"] >= (vol_baseline * min_vol_factor)

        if valid_candlestick and volume_filter:
            logger.info("🎯 SNIPER SETUP: Bullish Rejection Confirmed on Candle Close.")
            return True

        return False