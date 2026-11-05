import math
from typing import Sequence, Optional
from app.models.schemas import CandleRecord, AggregatedCandle

def calculate_sma(closes: Sequence[float], period: int = 14) -> list[Optional[float]]:
    result: list[Optional[float]] = [None] * len(closes)
    if len(closes) < period:
        return result
    current_sum = sum(closes[:period])
    result[period - 1] = current_sum / period
    for i in range(period, len(closes)):
        current_sum += closes[i] - closes[i - period]
        result[i] = current_sum / period
    return result

def calculate_ema(closes: Sequence[float], period: int = 14) -> list[Optional[float]]:
    result: list[Optional[float]] = [None] * len(closes)
    if len(closes) < period:
        return result
    multiplier = 2.0 / (period + 1.0)
    sma_init = sum(closes[:period]) / period
    result[period - 1] = sma_init
    current_ema = sma_init
    for i in range(period, len(closes)):
        current_ema = (closes[i] - current_ema) * multiplier + current_ema
        result[i] = current_ema
    return result

def calculate_rsi(closes: Sequence[float], period: int = 14) -> list[Optional[float]]:
    result: list[Optional[float]] = [None] * len(closes)
    if len(closes) <= period:
        return result
    
    gains: list[float] = []
    losses: list[float] = []
    for i in range(1, len(closes)):
        change = closes[i] - closes[i - 1]
        gains.append(max(change, 0.0))
        losses.append(max(-change, 0.0))

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    if avg_loss == 0.0:
        result[period] = 100.0
    else:
        rs = avg_gain / avg_loss
        result[period] = 100.0 - (100.0 / (1.0 + rs))

    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        if avg_loss == 0.0:
            result[i + 1] = 100.0
        else:
            rs = avg_gain / avg_loss
            result[i + 1] = 100.0 - (100.0 / (1.0 + rs))

    return result

def calculate_macd(
    closes: Sequence[float],
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9
) -> dict[str, list[Optional[float]]]:
    fast_ema = calculate_ema(closes, fast_period)
    slow_ema = calculate_ema(closes, slow_period)
    
    macd_line: list[Optional[float]] = [None] * len(closes)
    valid_macd_values: list[float] = []
    first_valid_idx = None

    for i in range(len(closes)):
        if fast_ema[i] is not None and slow_ema[i] is not None:
            val = fast_ema[i] - slow_ema[i]  # type: ignore
            macd_line[i] = val
            valid_macd_values.append(val)
            if first_valid_idx is None:
                first_valid_idx = i

    signal_line: list[Optional[float]] = [None] * len(closes)
    histogram: list[Optional[float]] = [None] * len(closes)

    if first_valid_idx is not None and len(valid_macd_values) >= signal_period:
        valid_signal = calculate_ema(valid_macd_values, signal_period)
        for j, sig_val in enumerate(valid_signal):
            idx = first_valid_idx + j
            signal_line[idx] = sig_val
            if macd_line[idx] is not None and sig_val is not None:
                histogram[idx] = macd_line[idx] - sig_val  # type: ignore

    return {
        "macd": macd_line,
        "signal": signal_line,
        "histogram": histogram
    }

def calculate_bollinger_bands(
    closes: Sequence[float],
    period: int = 20,
    std_dev: float = 2.0
) -> dict[str, list[Optional[float]]]:
    sma = calculate_sma(closes, period)
    upper: list[Optional[float]] = [None] * len(closes)
    lower: list[Optional[float]] = [None] * len(closes)

    for i in range(period - 1, len(closes)):
        window = closes[i - period + 1 : i + 1]
        mean = sma[i]
        variance = sum((x - mean) ** 2 for x in window) / period  # type: ignore
        stdev = math.sqrt(variance)
        upper[i] = mean + (std_dev * stdev)  # type: ignore
        lower[i] = mean - (std_dev * stdev)  # type: ignore

    return {
        "middle": sma,
        "upper": upper,
        "lower": lower
    }

def calculate_vwap(candles: Sequence[CandleRecord | AggregatedCandle]) -> list[Optional[float]]:
    """Calculates VWAP resetting at 00:00:00 UTC daily session."""
    result: list[Optional[float]] = []
    cumulative_pv = 0.0
    cumulative_vol = 0.0
    current_day = None

    for c in candles:
        day = c.open_time // (86400 * 1000)
        if current_day != day:
            current_day = day
            cumulative_pv = 0.0
            cumulative_vol = 0.0

        typical_price = (c.high + c.low + c.close) / 3.0
        cumulative_pv += typical_price * c.volume
        cumulative_vol += c.volume

        if cumulative_vol > 0:
            result.append(cumulative_pv / cumulative_vol)
        else:
            result.append(typical_price)

    return result

def calculate_stochastic(
    candles: Sequence[CandleRecord | AggregatedCandle],
    k_period: int = 14,
    d_period: int = 3
) -> dict[str, list[Optional[float]]]:
    k_values: list[Optional[float]] = [None] * len(candles)
    for i in range(k_period - 1, len(candles)):
        window = candles[i - k_period + 1 : i + 1]
        low_min = min(c.low for c in window)
        high_max = max(c.high for c in window)
        c_close = candles[i].close
        if high_max - low_min == 0:
            k_values[i] = 50.0
        else:
            k_values[i] = ((c_close - low_min) / (high_max - low_min)) * 100.0

    valid_k = [x for x in k_values if x is not None]
    d_raw = calculate_sma(valid_k, d_period) if valid_k else []
    
    d_values: list[Optional[float]] = [None] * len(candles)
    offset = k_period - 1
    for idx, d_val in enumerate(d_raw):
        d_values[offset + idx] = d_val

    return {"k": k_values, "d": d_values}

def calculate_atr(
    candles: Sequence[CandleRecord | AggregatedCandle],
    period: int = 14
) -> list[Optional[float]]:
    result: list[Optional[float]] = [None] * len(candles)
    if len(candles) <= period:
        return result

    tr_list: list[float] = [candles[0].high - candles[0].low]
    for i in range(1, len(candles)):
        hl = candles[i].high - candles[i].low
        hc = abs(candles[i].high - candles[i - 1].close)
        lc = abs(candles[i].low - candles[i - 1].close)
        tr_list.append(max(hl, hc, lc))

    atr = sum(tr_list[:period]) / period
    result[period - 1] = atr

    for i in range(period, len(candles)):
        atr = (atr * (period - 1) + tr_list[i]) / period
        result[i] = atr

    return result

def calculate_supertrend(
    candles: Sequence[CandleRecord | AggregatedCandle],
    period: int = 10,
    multiplier: float = 3.0
) -> dict[str, list[Optional[float | int]]]:
    atr = calculate_atr(candles, period)
    trend: list[Optional[int]] = [None] * len(candles) # 1 for bull, -1 for bear
    supertrend: list[Optional[float]] = [None] * len(candles)
    
    upper_band = [0.0] * len(candles)
    lower_band = [0.0] * len(candles)

    for i in range(period, len(candles)):
        hl2 = (candles[i].high + candles[i].low) / 2.0
        cur_atr = atr[i] or 0.0
        
        basic_upper = hl2 + (multiplier * cur_atr)
        basic_lower = hl2 - (multiplier * cur_atr)

        # Lower band adjustment
        if basic_lower > lower_band[i - 1] or candles[i - 1].close < lower_band[i - 1]:
            lower_band[i] = basic_lower
        else:
            lower_band[i] = lower_band[i - 1]

        # Upper band adjustment
        if basic_upper < upper_band[i - 1] or candles[i - 1].close > upper_band[i - 1]:
            upper_band[i] = basic_upper
        else:
            upper_band[i] = upper_band[i - 1]

        prev_trend = trend[i - 1] if trend[i - 1] is not None else 1
        if prev_trend == 1:
            if candles[i].close < lower_band[i]:
                current_trend = -1
                st = upper_band[i]
            else:
                current_trend = 1
                st = lower_band[i]
        else:
            if candles[i].close > upper_band[i]:
                current_trend = 1
                st = lower_band[i]
            else:
                current_trend = -1
                st = upper_band[i]

        trend[i] = current_trend
        supertrend[i] = st

    return {"supertrend": supertrend, "trend": trend}

def calculate_obv(candles: Sequence[CandleRecord | AggregatedCandle]) -> list[float]:
    if not candles:
        return []
    result = [0.0]
    for i in range(1, len(candles)):
        if candles[i].close > candles[i - 1].close:
            result.append(result[-1] + candles[i].volume)
        elif candles[i].close < candles[i - 1].close:
            result.append(result[-1] - candles[i].volume)
        else:
            result.append(result[-1])
    return result

def calculate_cci(
    candles: Sequence[CandleRecord | AggregatedCandle],
    period: int = 20
) -> list[Optional[float]]:
    result: list[Optional[float]] = [None] * len(candles)
    if len(candles) < period:
        return result
    
    tp_list = [(c.high + c.low + c.close) / 3.0 for c in candles]
    tp_sma = calculate_sma(tp_list, period)

    for i in range(period - 1, len(candles)):
        window = tp_list[i - period + 1 : i + 1]
        mean = tp_sma[i] or 0.0
        mean_dev = sum(abs(x - mean) for x in window) / period
        if mean_dev == 0:
            result[i] = 0.0
        else:
            result[i] = (tp_list[i] - mean) / (0.015 * mean_dev)

    return result

def calculate_williams_r(
    candles: Sequence[CandleRecord | AggregatedCandle],
    period: int = 14
) -> list[Optional[float]]:
    result: list[Optional[float]] = [None] * len(candles)
    for i in range(period - 1, len(candles)):
        window = candles[i - period + 1 : i + 1]
        high_max = max(c.high for c in window)
        low_min = min(c.low for c in window)
        c_close = candles[i].close
        if high_max - low_min == 0:
            result[i] = -50.0
        else:
            result[i] = ((high_max - c_close) / (high_max - low_min)) * -100.0
    return result

def calculate_donchian_channels(
    candles: Sequence[CandleRecord | AggregatedCandle],
    period: int = 20
) -> dict[str, list[Optional[float]]]:
    upper: list[Optional[float]] = [None] * len(candles)
    lower: list[Optional[float]] = [None] * len(candles)
    middle: list[Optional[float]] = [None] * len(candles)

    for i in range(period - 1, len(candles)):
        window = candles[i - period + 1 : i + 1]
        hi = max(c.high for c in window)
        lo = min(c.low for c in window)
        upper[i] = hi
        lower[i] = lo
        middle[i] = (hi + lo) / 2.0

    return {"upper": upper, "middle": middle, "lower": lower}
