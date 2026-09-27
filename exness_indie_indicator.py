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

    vol_ok = (v0 >= vol_avg * 0.55)

    # 2. BEARISH SETUPS
    macro_down = (c0 < e200) or (e10 < e15 and c0 < e15) or (o0 >= ribbon_bottom and c0 < ribbon_bottom) or (h0 >= ribbon_bottom and c0 < ribbon_bottom)
    pull_tested_bear = h0 >= (ribbon_bottom * 0.9995)
    closed_below_ribbon = c0 < ribbon_top

    # 2A. Direct Pinbar Rejection
    is_bear_pin = (
        pull_tested_bear and closed_below_ribbon and
        (upper_wick >= candle_range * 0.35) and
        (upper_wick >= lower_wick * 1.5) and
        (lower_wick <= candle_range * 0.25) and
        (c0 <= (h0 + l0) / 2) and vol_ok
    )

    # 2B. Direct Strong Momentum Breakdown (Solid Red Breakdown Bar)
    is_strong_bear = (
        pull_tested_bear and closed_below_ribbon and
        (c0 < o0) and
        (body_size >= candle_range * 0.45) and
        (lower_wick <= candle_range * 0.20) and
        (c0 < ribbon_bottom) and
        (c0 <= l0 + candle_range * 0.30) and
        vol_ok
    )

    # 2C. 2-Candle Bearish Confirmation
    prev_tested_ema = (h1 >= min(ema10[1], ema15[1]) * 0.9995)
    curr_near_ema = (h0 >= ribbon_bottom * 0.997)
    curr_bear_confirm = (
        (c0 < o0) and
        (body_size >= candle_range * 0.40) and
        (lower_wick <= candle_range * 0.25) and
        (c0 <= c1) and
        (c0 < ribbon_bottom) and
        (not is_bear_pin) and
        (not is_strong_bear) and
        vol_ok
    )
    is_2candle_bear = prev_tested_ema and curr_near_ema and curr_bear_confirm

    bear_signal = macro_down and (is_bear_pin or is_strong_bear or is_2candle_bear)

    # 3. BULLISH SETUPS
    macro_up = (c0 > e200) or (e10 > e15 and c0 > e15) or (o0 <= ribbon_top and c0 > ribbon_top) or (l0 <= ribbon_top and c0 > ribbon_top)
    pull_tested_bull = l0 <= (ribbon_top * 1.0005)
    closed_above_ribbon = c0 > ribbon_bottom

    # 3A. Bullish Pinbar Rejection
    is_bull_pin = (
        pull_tested_bull and closed_above_ribbon and
        (lower_wick >= candle_range * 0.35) and
        (lower_wick >= upper_wick * 1.5) and
        (upper_wick <= candle_range * 0.25) and
        (c0 >= (h0 + l0) / 2) and vol_ok
    )

    # 3B. Bullish Engulfing / Solid Expansion off 10/15 EMA
    solid_green_body = (
        (c0 > o0) and
        (body_size >= candle_range * 0.45) and
        (upper_wick <= candle_range * 0.25) and
        (c0 > ribbon_top)
    )
    engulfs_prev = (
        (c0 >= max(c1, o1)) and
        (o0 <= min(c1, o1) * 1.002)
    )
    breaks_prev_high = (c0 > h1) and (body_size >= candle_range * 0.50)

    is_bull_eng = pull_tested_bull and closed_above_ribbon and solid_green_body and (engulfs_prev or breaks_prev_high) and vol_ok

    bull_signal = macro_up and (is_bull_pin or is_bull_eng)

    # 4. Markers
    bull_marker = plot.Marker(l0, text="▲ BUY") if bull_signal else plot.Marker(math.nan)
    bear_marker = plot.Marker(h0, text="▼ SELL") if bear_signal else plot.Marker(math.nan)

    return e10, e15, e200, bull_marker, bear_marker
