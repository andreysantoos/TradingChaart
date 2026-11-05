import pytest
from app.models.schemas import CandleRecord
from app.engine.indicators import (
    calculate_sma,
    calculate_ema,
    calculate_rsi,
    calculate_macd,
    calculate_bollinger_bands,
    calculate_vwap,
    calculate_atr,
    calculate_obv
)

def test_sma_calculation():
    data = [10.0, 20.0, 30.0, 40.0, 50.0]
    sma3 = calculate_sma(data, period=3)
    assert sma3[0] is None
    assert sma3[1] is None
    assert sma3[2] == pytest.approx(20.0)  # (10+20+30)/3
    assert sma3[3] == pytest.approx(30.0)  # (20+30+40)/3
    assert sma3[4] == pytest.approx(40.0)  # (30+40+50)/3

def test_ema_calculation():
    data = [10.0, 11.0, 12.0, 13.0, 14.0]
    ema3 = calculate_ema(data, period=3)
    # SMA init = (10+11+12)/3 = 11.0
    assert ema3[2] == pytest.approx(11.0)
    # Multiplier = 2/(3+1) = 0.5
    # EMA[3] = (13 - 11)*0.5 + 11 = 12.0
    assert ema3[3] == pytest.approx(12.0)
    # EMA[4] = (14 - 12)*0.5 + 12 = 13.0
    assert ema3[4] == pytest.approx(13.0)

def test_rsi_bounds():
    # Continual upward trend should result in high RSI
    up_data = [float(i) for i in range(1, 30)]
    rsi_up = calculate_rsi(up_data, period=14)
    assert rsi_up[-1] is not None
    assert rsi_up[-1] > 95.0

    # Continual downward trend should result in low RSI
    down_data = [float(100 - i) for i in range(30)]
    rsi_down = calculate_rsi(down_data, period=14)
    assert rsi_down[-1] is not None
    assert rsi_down[-1] < 5.0

def test_bollinger_bands():
    data = [100.0] * 20
    bb = calculate_bollinger_bands(data, period=20, std_dev=2.0)
    # When data has zero variance, upper == middle == lower
    assert bb["middle"][19] == pytest.approx(100.0)
    assert bb["upper"][19] == pytest.approx(100.0)
    assert bb["lower"][19] == pytest.approx(100.0)

def test_obv():
    candles = [
        CandleRecord(symbol="TEST", timeframe="1m", open_time=0, close_time=60, open=10, high=12, low=9, close=10, volume=100),
        CandleRecord(symbol="TEST", timeframe="1m", open_time=60, close_time=120, open=10, high=15, low=10, close=12, volume=200),
        CandleRecord(symbol="TEST", timeframe="1m", open_time=120, close_time=180, open=12, high=13, low=8, close=9, volume=150),
    ]
    obv = calculate_obv(candles)
    assert obv[0] == 0.0
    assert obv[1] == 200.0  # close went from 10 to 12 (+200)
    assert obv[2] == 50.0   # close went from 12 to 9 (-150)
