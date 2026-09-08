import pandas as pd
import logging

logger = logging.getLogger("StrategyEngine")

class PullbackRejectionStrategy:
    def __init__(self, fast_ema_col: str = "EMA_10", slow_ema_col: str = "EMA_200"):
        self.fast_ema = fast_ema_col
        self.slow_ema = slow_ema_col
        self.slope_col = f"{slow_ema_col}_slope"

    def evaluate_bearish_setup(self, df: pd.DataFrame) -> bool:
        """
        Evaluates the exact Bearish Trend Continuation + Pullback Rejection setup criteria.
        Guarantees evaluation only on CLOSED historical bars.
        """
        if len(df) < 5:
            return False

        # Index Mapping:
        # -1 is current forming candle (IGNORED to prevent repainting)
        # -2 is the structural trigger candle (just closed)
        # -3 is the structural pullback/rejection candle
        # -4 is the initiation trend confirmation candle
        
        c_trigger = df.iloc[-2]
        c_reject = df.iloc[-3]
        c_prior = df.iloc[-4]

        # 1. Structural Regime Trend Validation
        trend_bearish = (c_reject[self.fast_ema] < c_reject[self.slow_ema]) and (c_reject[self.slope_col] < 0)
        price_below_structural_high = c_reject["close"] < c_reject[self.slow_ema]

        if not (trend_bearish and price_below_structural_high):
            return False

        # 2. Structural Pullback & Dynamic Rejection Validation
        # High of candle touches or approaches within 0.05% of Fast EMA zone
        pullback_touches_ema = c_reject["high"] >= (c_reject[self.fast_ema] * 0.9995)
        closes_below_ema = c_reject["close"] < c_reject[self.fast_ema]
        
        # Upper wick rejection signature (Wick represents at least 40% of overall candle range)
        candle_range = c_reject["high"] - c_reject["low"]
        real_body_high = max(c_reject["open"], c_reject["close"])
        upper_wick = c_reject["high"] - real_body_high
        
        has_rejection_wick = (upper_wick >= candle_range * 0.40) if candle_range > 0 else False
        is_bearish_engulfing = (c_reject["close"] < c_reject["open"]) and (c_reject["open"] >= c_prior["close"])

        valid_rejection = pullback_touches_ema and closes_below_ema and (has_rejection_wick or is_bearish_engulfing)

        # 3. Dynamic Bearish Expansion (Continuation Confirmation)
        strong_bearish_expansion = c_trigger["close"] < c_reject["low"]
        volume_confirmation = c_trigger["volume"] >= df["volume"].rolling(10).mean().iloc[-2]

        if valid_rejection and strong_bearish_expansion and volume_confirmation:
            logger.info("CRITICAL STRATEGY CONDITION FOUND: Bearish Setup Confirmed.")
            return True

        return False

    def evaluate_bullish_setup(self, df: pd.DataFrame) -> bool:
        """
        Evaluates the exact Bullish Trend Continuation + Pullback Rejection setup criteria.
        Guarantees evaluation only on CLOSED historical bars.
        """
        if len(df) < 5:
            return False

        # Index Mapping:
        # -1 is current forming candle (IGNORED to prevent repainting)
        # -2 is the structural trigger candle (just closed)
        # -3 is the structural pullback/rejection candle
        # -4 is the initiation trend confirmation candle
        
        c_trigger = df.iloc[-2]
        c_reject = df.iloc[-3]
        c_prior = df.iloc[-4]

        # 1. Structural Regime Trend Validation
        trend_bullish = (c_reject[self.fast_ema] > c_reject[self.slow_ema]) and (c_reject[self.slope_col] > 0)
        price_above_structural_low = c_reject["close"] > c_reject[self.slow_ema]

        if not (trend_bullish and price_above_structural_low):
            return False

        # 2. Structural Pullback & Dynamic Rejection Validation
        # Low of candle touches or approaches within 0.05% of Fast EMA zone
        pullback_touches_ema = c_reject["low"] <= (c_reject[self.fast_ema] * 1.0005)
        closes_above_ema = c_reject["close"] > c_reject[self.fast_ema]
        
        # Lower wick rejection signature (Wick represents at least 40% of overall candle range)
        candle_range = c_reject["high"] - c_reject["low"]
        real_body_low = min(c_reject["open"], c_reject["close"])
        lower_wick = real_body_low - c_reject["low"]
        
        has_rejection_wick = (lower_wick >= candle_range * 0.40) if candle_range > 0 else False
        is_bullish_engulfing = (c_reject["close"] > c_reject["open"]) and (c_reject["open"] <= c_prior["close"])

        valid_rejection = pullback_touches_ema and closes_above_ema and (has_rejection_wick or is_bullish_engulfing)

        # 3. Dynamic Bullish Expansion (Continuation Confirmation)
        strong_bullish_expansion = c_trigger["close"] > c_reject["high"]
        volume_confirmation = c_trigger["volume"] >= df["volume"].rolling(10).mean().iloc[-2]

        if valid_rejection and strong_bullish_expansion and volume_confirmation:
            logger.info("CRITICAL STRATEGY CONDITION FOUND: Bullish Setup Confirmed.")
            return True

        return False