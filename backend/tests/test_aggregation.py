import pytest
from app.models.schemas import CandleRecord
from app.engine.aggregation import aggregate_candles, get_window_start_time

def create_sample_1m_candle(minute_offset: int, open_p: float, high_p: float, low_p: float, close_p: float, vol: float = 1.0) -> CandleRecord:
    # 1700000100000 aligned to 15m boundary
    # 15m in ms = 900,000
    base_time = (1700000000000 // 900000) * 900000  # Exact 15m boundary
    open_time = base_time + (minute_offset * 60000)
    close_time = open_time + 59999
    return CandleRecord(
        symbol="BTCUSDT",
        timeframe="1m",
        open_time=open_time,
        close_time=close_time,
        open=open_p,
        high=high_p,
        low=low_p,
        close=close_p,
        volume=vol,
        quote_volume=vol * close_p,
        is_closed=True,
        origin="test"
    )

def test_aggregation_15m_complete():
    # Create 15 consecutive 1m candles starting at window boundary
    candles = []
    base_price = 50000.0
    for i in range(15):
        candles.append(
            create_sample_1m_candle(
                minute_offset=i,
                open_p=base_price + i,
                high_p=base_price + i + 10,
                low_p=base_price + i - 5,
                close_p=base_price + i + 2,
                vol=1.0
            )
        )
    
    aggs = aggregate_candles(candles, "15m", require_full_window=True)
    assert len(aggs) == 1
    agg = aggs[0]
    
    # Check open: first candle open
    assert agg.open == candles[0].open
    # Check close: last candle close
    assert agg.close == candles[-1].close
    # Check high: maximum across all
    assert agg.high == max(c.high for c in candles)
    # Check low: minimum across all
    assert agg.low == min(c.low for c in candles)
    # Check volume: sum of volume
    assert agg.volume == 15.0
    assert agg.constituent_count == 15
    assert agg.is_complete is True

def test_aggregation_incomplete_window():
    # Only 14 candles instead of 15
    candles = [
        create_sample_1m_candle(i, 50000, 50010, 49990, 50005, 1.0)
        for i in range(14)
    ]
    # With require_full_window=True, it should skip incomplete windows
    aggs = aggregate_candles(candles, "15m", require_full_window=True)
    assert len(aggs) == 0

    # With require_full_window=False, it returns marked as incomplete
    aggs_partial = aggregate_candles(candles, "15m", require_full_window=False)
    assert len(aggs_partial) == 1
    assert aggs_partial[0].is_complete is False
    assert aggs_partial[0].constituent_count == 14
