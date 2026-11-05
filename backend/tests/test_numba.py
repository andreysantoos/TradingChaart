import numpy as np
import pytest
from app.engine.numba_indicators import (
    numba_sma,
    numba_ema,
    numba_rsi,
    numba_bollinger_bands,
    numba_atr,
    numba_supertrend
)

def test_numba_sma():
    arr = np.array([10.0, 20.0, 30.0, 40.0, 50.0], dtype=np.float64)
    res = numba_sma(arr, 3)
    assert np.isnan(res[0])
    assert np.isnan(res[1])
    assert res[2] == pytest.approx(20.0)
    assert res[3] == pytest.approx(30.0)
    assert res[4] == pytest.approx(40.0)

def test_numba_ema():
    arr = np.array([10.0, 11.0, 12.0, 13.0, 14.0], dtype=np.float64)
    res = numba_ema(arr, 3)
    assert res[2] == pytest.approx(11.0)
    assert res[3] == pytest.approx(12.0)
    assert res[4] == pytest.approx(13.0)

def test_numba_rsi():
    # Continual up trend
    arr = np.arange(1.0, 31.0, dtype=np.float64)
    res = numba_rsi(arr, 14)
    assert res[-1] > 95.0

def test_numba_bollinger():
    arr = np.full(20, 100.0, dtype=np.float64)
    middle, upper, lower = numba_bollinger_bands(arr, 20, 2.0)
    assert middle[-1] == pytest.approx(100.0)
    assert upper[-1] == pytest.approx(100.0)
    assert lower[-1] == pytest.approx(100.0)
