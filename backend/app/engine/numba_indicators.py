import numpy as np
from numba import njit

@njit(fastmath=True)
def numba_sma(closes: np.ndarray, period: int) -> np.ndarray:
    n = len(closes)
    out = np.full(n, np.nan, dtype=np.float64)
    if n < period:
        return out
    
    current_sum = 0.0
    for i in range(period):
        current_sum += closes[i]
    out[period - 1] = current_sum / period

    for i in range(period, n):
        current_sum += closes[i] - closes[i - period]
        out[i] = current_sum / period
    return out

@njit(fastmath=True)
def numba_ema(closes: np.ndarray, period: int) -> np.ndarray:
    n = len(closes)
    out = np.full(n, np.nan, dtype=np.float64)
    if n < period:
        return out
    
    alpha = 2.0 / (period + 1.0)
    # Init with SMA
    init_sum = 0.0
    for i in range(period):
        init_sum += closes[i]
    val = init_sum / period
    out[period - 1] = val

    for i in range(period, n):
        val = (closes[i] - val) * alpha + val
        out[i] = val
    return out

@njit(fastmath=True)
def numba_rsi(closes: np.ndarray, period: int) -> np.ndarray:
    n = len(closes)
    out = np.full(n, np.nan, dtype=np.float64)
    if n <= period:
        return out

    gains = np.zeros(n - 1, dtype=np.float64)
    losses = np.zeros(n - 1, dtype=np.float64)

    for i in range(1, n):
        diff = closes[i] - closes[i - 1]
        if diff > 0:
            gains[i - 1] = diff
        else:
            losses[i - 1] = -diff

    avg_gain = 0.0
    avg_loss = 0.0
    for i in range(period):
        avg_gain += gains[i]
        avg_loss += losses[i]
    avg_gain /= period
    avg_loss /= period

    if avg_loss == 0.0:
        out[period] = 100.0
    else:
        rs = avg_gain / avg_loss
        out[period] = 100.0 - (100.0 / (1.0 + rs))

    for i in range(period, n - 1):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        if avg_loss == 0.0:
            out[i + 1] = 100.0
        else:
            rs = avg_gain / avg_loss
            out[i + 1] = 100.0 - (100.0 / (1.0 + rs))

    return out

@njit(fastmath=True)
def numba_bollinger_bands(closes: np.ndarray, period: int, std_dev: float):
    n = len(closes)
    middle = numba_sma(closes, period)
    upper = np.full(n, np.nan, dtype=np.float64)
    lower = np.full(n, np.nan, dtype=np.float64)

    for i in range(period - 1, n):
        m = middle[i]
        var_sum = 0.0
        for j in range(i - period + 1, i + 1):
            d = closes[j] - m
            var_sum += d * d
        stdev = np.sqrt(var_sum / period)
        upper[i] = m + (std_dev * stdev)
        lower[i] = m - (std_dev * stdev)

    return middle, upper, lower

@njit(fastmath=True)
def numba_atr(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int) -> np.ndarray:
    n = len(closes)
    out = np.full(n, np.nan, dtype=np.float64)
    if n <= period:
        return out

    tr = np.zeros(n, dtype=np.float64)
    tr[0] = highs[0] - lows[0]
    for i in range(1, n):
        hl = highs[i] - lows[i]
        hc = abs(highs[i] - closes[i - 1])
        lc = abs(lows[i] - closes[i - 1])
        m = hl
        if hc > m:
            m = hc
        if lc > m:
            m = lc
        tr[i] = m

    atr_sum = 0.0
    for i in range(period):
        atr_sum += tr[i]
    atr = atr_sum / period
    out[period - 1] = atr

    for i in range(period, n):
        atr = (atr * (period - 1) + tr[i]) / period
        out[i] = atr

    return out

@njit(fastmath=True)
def numba_supertrend(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int, multiplier: float):
    n = len(closes)
    atr = numba_atr(highs, lows, closes, period)
    trend = np.zeros(n, dtype=np.int32)
    st = np.full(n, np.nan, dtype=np.float64)

    upper_band = np.zeros(n, dtype=np.float64)
    lower_band = np.zeros(n, dtype=np.float64)

    for i in range(period, n):
        hl2 = (highs[i] + lows[i]) / 2.0
        cur_atr = atr[i]
        basic_upper = hl2 + (multiplier * cur_atr)
        basic_lower = hl2 - (multiplier * cur_atr)

        if basic_lower > lower_band[i - 1] or closes[i - 1] < lower_band[i - 1]:
            lower_band[i] = basic_lower
        else:
            lower_band[i] = lower_band[i - 1]

        if basic_upper < upper_band[i - 1] or closes[i - 1] > upper_band[i - 1]:
            upper_band[i] = basic_upper
        else:
            upper_band[i] = upper_band[i - 1]

        prev_trend = trend[i - 1] if i > period else 1
        if prev_trend == 1:
            if closes[i] < lower_band[i]:
                current_trend = -1
                cur_st = upper_band[i]
            else:
                current_trend = 1
                cur_st = lower_band[i]
        else:
            if closes[i] > upper_band[i]:
                current_trend = 1
                cur_st = lower_band[i]
            else:
                current_trend = -1
                cur_st = upper_band[i]

        trend[i] = current_trend
        st[i] = cur_st

    return st, trend
