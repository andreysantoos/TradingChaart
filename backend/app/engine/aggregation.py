from typing import Sequence
from app.models.schemas import CandleRecord, AggregatedCandle

TIMEFRAME_MINUTES: dict[str, int] = {
    "1m": 1,
    "5m": 5,
    "15m": 15,
    "30m": 30,
    "1h": 60,
    "4h": 240,
    "1d": 1440,
    "1w": 10080
}

# Thursday 1970-01-01 to Monday 1970-01-05 offset in ms
WEEK_OFFSET_MS = 4 * 86400 * 1000

def get_window_start_time(open_time_ms: int, timeframe: str) -> int:
    """Computes the UTC-aligned window start time for a given timestamp and timeframe."""
    minutes = TIMEFRAME_MINUTES.get(timeframe, 1)
    duration_ms = minutes * 60 * 1000
    
    if timeframe == "1w":
        # Monday 00:00:00 UTC alignment
        return ((open_time_ms - WEEK_OFFSET_MS) // duration_ms) * duration_ms + WEEK_OFFSET_MS
    else:
        return (open_time_ms // duration_ms) * duration_ms

def aggregate_candles(
    candles_1m: Sequence[CandleRecord],
    target_timeframe: str,
    require_full_window: bool = True
) -> list[AggregatedCandle]:
    """
    Aggregates a sequence of 1-minute candles into the target timeframe according to canonical rules:
    - open: open of the first 1m candle
    - high: max high among all candles in window
    - low: min low among all candles in window
    - close: close of the last 1m candle
    - volume: sum of volume
    - quote_volume: sum of quote_volume
    - completeness check: constituent count == expected count
    """
    if target_timeframe == "1m":
        return [
            AggregatedCandle(
                symbol=c.symbol,
                timeframe="1m",
                open_time=c.open_time,
                close_time=c.close_time,
                open=c.open,
                high=c.high,
                low=c.low,
                close=c.close,
                volume=c.volume,
                quote_volume=c.quote_volume or 0.0,
                constituent_count=1,
                expected_count=1,
                is_complete=True
            )
            for c in candles_1m
        ]

    expected_count = TIMEFRAME_MINUTES.get(target_timeframe, 1)
    duration_ms = expected_count * 60 * 1000
    
    # Group candles by window start time
    windows: dict[int, list[CandleRecord]] = {}
    for c in candles_1m:
        w_start = get_window_start_time(c.open_time, target_timeframe)
        if w_start not in windows:
            windows[w_start] = []
        windows[w_start].append(c)

    aggregated: list[AggregatedCandle] = []
    for w_start in sorted(windows.keys()):
        group = sorted(windows[w_start], key=lambda x: x.open_time)
        count = len(group)
        is_complete = (count == expected_count)
        
        if require_full_window and not is_complete:
            continue
            
        w_close = w_start + duration_ms - 1
        agg = AggregatedCandle(
            symbol=group[0].symbol,
            timeframe=target_timeframe,
            open_time=w_start,
            close_time=w_close,
            open=group[0].open,
            high=max(c.high for c in group),
            low=min(c.low for c in group),
            close=group[-1].close,
            volume=sum(c.volume for c in group),
            quote_volume=sum(c.quote_volume or 0.0 for c in group),
            constituent_count=count,
            expected_count=expected_count,
            is_complete=is_complete
        )
        aggregated.append(agg)
        
    return aggregated
