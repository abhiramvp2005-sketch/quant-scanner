import pandas as pd
import logging
from typing import Tuple

logger = logging.getLogger("StrategyEngine")

class PullbackRejectionStrategy:
    def __init__(
        self, 
        fast_ema_col: str = "EMA_10", 
        mid_ema_col: str = "EMA_15", 
        slow_ema_col: str = "EMA_200", 
        min_atr_factor: float = 0.35
    ):
        self.fast_ema = fast_ema_col
        self.mid_ema = mid_ema_col
        self.slow_ema = slow_ema_col
        self.min_atr_factor = min_atr_factor

    def evaluate_bearish_setup(self, df: pd.DataFrame) -> Tuple[bool, str, float]:
        """
        Sniper Bearish Pullback Strategy on 10/15 EMA Ribbon:
        Supports:
        1. Direct Rejection (Pinbar off 10/15 EMA)
        2. Direct Strong Momentum Rejection (Solid Red Breakdown Bar from 10/15 EMA)
        3. 2-Candle Bearish Confirmation near 10/15 EMA
        Returns: (is_valid, pattern_name, stop_loss_price)
        """
        if len(df) < 20:
            return False, "", 0.0

        c_reject = df.iloc[-2]
        c_prev = df.iloc[-3]

        ema_fast = c_reject.get(self.fast_ema)
        ema_mid = c_reject.get(self.mid_ema, ema_fast)
        ema_slow = c_reject.get(self.slow_ema)

        if pd.isna(ema_fast) or pd.isna(ema_slow):
            return False, "", 0.0

        ribbon_bottom = min(ema_fast, ema_mid)
        ribbon_top = max(ema_fast, ema_mid)
        atr_val = c_reject.get("ATR")

        candle_range = c_reject["high"] - c_reject["low"]
        if candle_range <= 0:
            return False, "", 0.0

        # Minimum Displacement Check (Eliminate micro-choppy bars)
        if pd.notna(atr_val) and atr_val > 0 and candle_range < (atr_val * 0.40):
            return False, "", 0.0

        real_body_high = max(c_reject["open"], c_reject["close"])
        real_body_low = min(c_reject["open"], c_reject["close"])
        upper_wick = c_reject["high"] - real_body_high
        lower_wick = real_body_low - c_reject["low"]
        body_size = abs(c_reject["close"] - c_reject["open"])
        vol_baseline = df["volume"].rolling(10).mean().iloc[-2]

        # 1. Macro Trend Regime:
        macro_downtrend = (
            (c_reject["close"] < ema_slow) or 
            (ema_fast < ema_mid and c_reject["close"] < ema_mid) or 
            (c_reject["open"] >= ribbon_bottom and c_reject["close"] < ribbon_bottom) or
            (c_reject["high"] >= ribbon_bottom and c_reject["close"] < ribbon_bottom)
        )
        if not macro_downtrend:
            return False, "", 0.0

        # ---------------- PATTERN 1: DIRECT REJECTION FROM EMAs ----------------
        # Strict Ribbon Touch: High must test into the 10/15 EMA ribbon
        pullback_tested = c_reject["high"] >= (ribbon_bottom * 0.9995)
        closed_below = c_reject["close"] < ribbon_top

        if not (pullback_tested and closed_below):
            return False, "", 0.0

        # 1A. Genuine Bearish Pinbar Rejection off Ribbon:
        # - Dominant Upper Wick >= 35% of range
        # - Upper Wick >= 1.5x Lower Wick AND Lower Wick <= 25% of range (no bottom rejection)
        # - Closes in lower half of candle
        is_pinbar = (
            (upper_wick >= candle_range * 0.35) and
            (upper_wick >= lower_wick * 1.5) and
            (lower_wick <= candle_range * 0.25) and
            (c_reject["close"] <= (c_reject["high"] + c_reject["low"]) / 2)
        )

        # 1B. Direct Strong Momentum Rejection (Solid Red Breakdown Bar):
        # - Must be a solid red candle (body >= 45% of range, NOT a doji)
        # - Small lower wick <= 20% of range (no bounce from lows)
        # - Closes firmly below ribbon
        is_strong_rejection = (
            (c_reject["close"] < c_reject["open"]) and
            (body_size >= candle_range * 0.45) and
            (lower_wick <= candle_range * 0.20) and
            (c_reject["close"] < ribbon_bottom) and
            (c_reject["close"] <= c_reject["low"] + candle_range * 0.30)
        )

        volume_ok = (c_reject["volume"] >= vol_baseline * 0.55) if (pd.notna(vol_baseline) and vol_baseline > 0) else True

        is_direct_entry = (is_pinbar or is_strong_rejection) and volume_ok

        # ---------------- PATTERN 2: 2-CANDLE BEARISH CONFIRMATION NEAR EMAs ----------------
        prev_tested_ema = c_prev["high"] >= (min(c_prev.get(self.fast_ema, ema_fast), c_prev.get(self.mid_ema, ema_mid)) * 0.999)
        curr_near_ema = (c_reject["high"] >= ribbon_bottom * 0.997)
        curr_bearish_confirm = (
            (c_reject["close"] < c_reject["open"]) and
            (body_size >= candle_range * 0.40) and
            (lower_wick <= candle_range * 0.25) and
            (c_reject["close"] <= c_prev["close"]) and
            (c_reject["close"] < ribbon_bottom) and
            not is_direct_entry
        )
        is_2candle_entry = (prev_tested_ema and curr_near_ema and curr_bearish_confirm and volume_ok)

        if is_direct_entry:
            pattern_name = "Direct Rejection (Pinbar)" if is_pinbar else "Direct Strong Rejection"
            sl = c_reject["high"]
            logger.info(f"🎯 SNIPER BEARISH SETUP: {pattern_name} Confirmed.")
            return True, pattern_name, sl

        if is_2candle_entry:
            pattern_name = "2-Candle Bearish Confirmation"
            sl = max(c_reject["high"], c_prev["high"])
            logger.info(f"🎯 SNIPER BEARISH SETUP: {pattern_name} Confirmed.")
            return True, pattern_name, sl

        return False, "", 0.0

    def evaluate_bullish_setup(self, df: pd.DataFrame) -> Tuple[bool, str, float]:
        """
        Sniper Bullish Pullback Strategy on 10/15 EMA Ribbon:
        Evaluates Bullish Rejection Pinbars AND Bullish Engulfing patterns.
        Returns: (is_valid, pattern_name, stop_loss_price)
        """
        if len(df) < 20:
            return False, "", 0.0

        c_reject = df.iloc[-2]
        c_prev = df.iloc[-3]

        ema_fast = c_reject.get(self.fast_ema)
        ema_mid = c_reject.get(self.mid_ema, ema_fast)
        ema_slow = c_reject.get(self.slow_ema)

        if pd.isna(ema_fast) or pd.isna(ema_slow):
            return False, "", 0.0

        ribbon_top = max(ema_fast, ema_mid)
        ribbon_bottom = min(ema_fast, ema_mid)
        atr_val = c_reject.get("ATR")

        # 1. Macro Trend Regime:
        macro_uptrend = (
            (c_reject["close"] > ema_slow) or 
            (ema_fast > ema_mid and c_reject["close"] > ema_mid) or
            (c_reject["open"] <= ribbon_top and c_reject["close"] > ribbon_top) or
            (c_reject["low"] <= ribbon_top and c_reject["close"] > ribbon_top)
        )
        if not macro_uptrend:
            return False, "", 0.0

        # 2. Dynamic EMA Pocket Test:
        # STRICT CONDITION: Candle Low must touch / test the 10/15 EMA ribbon
        pullback_tested_zone = c_reject["low"] <= (ribbon_top * 1.0005)
        closed_above_zone = c_reject["close"] > ribbon_bottom
        if not (pullback_tested_zone and closed_above_zone):
            return False, "", 0.0

        candle_range = c_reject["high"] - c_reject["low"]
        if candle_range <= 0:
            return False, "", 0.0

        # Minimum Displacement Check (Eliminate micro-choppy bars)
        if pd.notna(atr_val) and atr_val > 0 and candle_range < (atr_val * 0.40):
            return False, "", 0.0

        real_body_high = max(c_reject["open"], c_reject["close"])
        real_body_low = min(c_reject["open"], c_reject["close"])
        upper_wick = c_reject["high"] - real_body_high
        lower_wick = real_body_low - c_reject["low"]
        body_size = abs(c_reject["close"] - c_reject["open"])

        # Signature A: Bullish Pinbar Rejection off 10/15 EMA
        # - Dominant Lower Wick >= 35% of range
        # - Lower Wick >= 1.5x Upper Wick AND Upper Wick <= 25% of range
        # - Closes in upper half of candle
        has_pinbar = (
            (lower_wick >= candle_range * 0.35) and
            (lower_wick >= upper_wick * 1.5) and
            (upper_wick <= candle_range * 0.25) and
            (c_reject["close"] >= (c_reject["high"] + c_reject["low"]) / 2)
        )

        # Signature B: Bullish Engulfing / Solid Expansion off 10/15 EMA
        # - Must be a solid green candle (body >= 45% of range, NOT a doji)
        # - Small upper wick <= 25% of range (strong buying conviction into close)
        # - Closes firmly above ribbon top
        # - Physically engulfs prev body or breaks out past prev high with solid body
        solid_green_body = (
            (c_reject["close"] > c_reject["open"]) and
            (body_size >= candle_range * 0.45) and
            (upper_wick <= candle_range * 0.25) and
            (c_reject["close"] > ribbon_top)
        )
        
        engulfs_prev = (
            (c_reject["close"] >= max(c_prev["close"], c_prev["open"])) and
            (c_reject["open"] <= min(c_prev["close"], c_prev["open"]) * 1.002)
        )
        breaks_prev_high = (c_reject["close"] > c_prev["high"]) and (body_size >= candle_range * 0.50)

        is_engulfing = solid_green_body and (engulfs_prev or breaks_prev_high)

        if not (has_pinbar or is_engulfing):
            return False, "", 0.0

        # 5. Volume Filter
        vol_baseline = df["volume"].rolling(10).mean().iloc[-2]
        min_vol_factor = 0.55
        volume_ok = (c_reject["volume"] >= vol_baseline * min_vol_factor) if (pd.notna(vol_baseline) and vol_baseline > 0) else True

        if volume_ok:
            pattern_name = "Bullish Rejection (Pinbar)" if has_pinbar else "Bullish Engulfing"
            sl = c_reject["low"]
            logger.info(f"🎯 SNIPER BULLISH SETUP: {pattern_name} Confirmed on 10/15 EMA.")
            return True, pattern_name, sl

        return False, "", 0.0