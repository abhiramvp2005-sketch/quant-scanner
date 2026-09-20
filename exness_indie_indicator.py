# indie:lang_version = 5
import math
from indie import indicator, plot, color, param
from indie.algorithms import Ema, Sma, Atr

@indicator('Sniper 10/15 EMA Ribbon Strategy', overlay_main_pane=True)
@param.int('fast_len', default=10, title='Fast EMA Length')
@param.int('mid_len', default=15, title='Mid EMA Length')
@param.int('slow_len', default=200, title='Macro EMA Length')
@param.int('atr_len', default=14, title='ATR Length')
@plot.line(color=color.WHITE, line_width=2, title="EMA 10")
@plot.line(color=color.GRAY, line_width=1, title="EMA 15")
@plot.line(color=color.RED, line_width=2, title="EMA 200")
@plot.marker(style=plot.marker_style.LABEL, color=color.GREEN, position=plot.marker_position.BELOW, title="Bullish Setup")
@plot.marker(style=plot.marker_style.LABEL, color=color.RED, position=plot.marker_position.ABOVE, title="Bearish Setup")
def Main(self, fast_len: int, mid_len: int, slow_len: int, atr_len: int):
    # 1. Indicators
    ema10 = Ema.new(self.close, fast_len)
    ema15 = Ema.new(self.close, mid_len)
    ema200 = Ema.new(self.close, slow_len)
    atr = Atr.new(atr_len)
    vol_sma = Sma.new(self.volume, 10)

    e10 = ema10[0]
    e15 = ema15[0]
    e200 = ema200[0]
    atr_val = atr[0]
    vol_avg = vol_sma[0]

    ribbon_bottom = min(e10, e15)
    ribbon_top = max(e10, e15)

    o0 = self.open[0]
    h0 = self.high[0]
    l0 = self.low[0]
    c0 = self.close[0]
    v0 = self.volume[0]

    o1 = self.open[1]
    h1 = self.high[1]
    l1 = self.low[1]
    c1 = self.close[1]

    candle_range = h0 - l0
    if candle_range <= 0:
        return e10, e15, e200, plot.Marker(math.nan), plot.Marker(math.nan)

    real_body_high = max(o0, c0)
    real_body_low = min(o0, c0)
    upper_wick = h0 - real_body_high
    lower_wick = real_body_low - l0
    body_size = abs(c0 - o0)

    vol_ok_pin = (v0 >= vol_avg * 0.60)
    vol_ok_eng = (v0 >= vol_avg * 0.85)

    # 2. BEARISH SETUPS
    macro_down = (c0 < e200) or (e10 < e15 and c0 < e15) or (o0 >= ribbon_bottom and c0 < ribbon_bottom)
    pull_tested_bear = h0 >= (ribbon_bottom * 0.9995)
    closed_below_ribbon = c0 < ribbon_top
    within_bear_prox = (ribbon_bottom - c0) <= (atr_val * 0.85)

    # 2A. Direct Pinbar Rejection
    is_bear_pin = (
        pull_tested_bear and closed_below_ribbon and within_bear_prox and
        (upper_wick >= candle_range * 0.35) and
        ((upper_wick >= lower_wick * 1.5) or (lower_wick <= candle_range * 0.25)) and
        (c0 <= (h0 + l0) / 2) and vol_ok_pin
    )

    # 2B. Direct Strong Momentum Breakdown
    is_strong_bear = (
        (c0 < o0) and
        (h0 >= ribbon_bottom * 0.9995) and
        (o0 >= ribbon_bottom * 0.998) and
        (c0 < ribbon_bottom) and
        within_bear_prox and
        ((upper_wick >= candle_range * 0.15) or (body_size >= candle_range * 0.50)) and
        vol_ok_pin
    )

    # 2C. 2-Candle Bearish Confirmation (Only fires on fresh rejection from EMA test)
    prev_tested_ema = (h1 >= min(ema10[1], ema15[1]) * 0.9995) and (c1 >= min(ema10[1], ema15[1]) * 0.995)
    curr_bear_confirm = (
        (c0 < o0) and
        (c0 < l1) and
        (c0 < ribbon_bottom) and
        (h0 >= ribbon_bottom * 0.996) and
        within_bear_prox and
        (not is_bear_pin) and
        (not is_strong_bear) and
        vol_ok_pin
    )
    is_2candle_bear = prev_tested_ema and curr_bear_confirm

    bear_signal = macro_down and (is_bear_pin or is_strong_bear or is_2candle_bear)

    # 3. BULLISH SETUPS
    macro_up = (c0 > e200) or (e10 > e15 and c0 > e15)
    pull_tested_bull = l0 <= (ribbon_top * 1.0005)
    closed_above_ribbon = c0 > ribbon_bottom
    within_bull_prox = (c0 - ribbon_top) <= (atr_val * 0.85)

    # 3A. Bullish Pinbar Rejection
    is_bull_pin = (
        pull_tested_bull and closed_above_ribbon and within_bull_prox and
        (lower_wick >= candle_range * 0.35) and
        ((lower_wick >= upper_wick * 1.5) or (upper_wick <= candle_range * 0.25)) and
        (c0 >= (h0 + l0) / 2) and vol_ok_pin
    )

    # 3B. Bullish Engulfing
    is_bull_eng = (
        pull_tested_bull and closed_above_ribbon and within_bull_prox and
        (c0 > o0) and
        (o0 <= max(c1, o1)) and
        (c0 >= max(c1, o1)) and
        (c0 > h1) and
        (lower_wick >= candle_range * 0.10) and vol_ok_eng
    )

    bull_signal = macro_up and (is_bull_pin or is_bull_eng)

    # 4. Markers
    bull_marker = plot.Marker(l0, text="▲ BUY") if bull_signal else plot.Marker(math.nan)
    bear_marker = plot.Marker(h0, text="▼ SELL") if bear_signal else plot.Marker(math.nan)

    return e10, e15, e200, bull_marker, bear_marker
