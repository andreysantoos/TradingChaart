import logging
import math
from typing import Optional
from app.core.config import settings
from app.models.schemas import AggregatedCandle, CandleRecord, ReconciliationRecord, ValidationStatus
from app.providers.binance_futures import BinanceFuturesProvider, binance_provider
from app.db.database import save_reconciliation, get_candles_1m
from app.engine.aggregation import aggregate_candles, TIMEFRAME_MINUTES

logger = logging.getLogger(__name__)

def is_close_enough(val_a: float, val_b: float, tol_pct: float) -> bool:
    if val_b == 0:
        return math.isclose(val_a, val_b, abs_tol=1e-8)
    diff = abs(val_a - val_b) / abs(val_b)
    return diff <= tol_pct

async def reconcile_window(
    symbol: str,
    timeframe: str,
    window_start_time: int,
    provider: Optional[BinanceFuturesProvider] = None
) -> ReconciliationRecord:
    """
    Performs independent reconciliation of an aggregated window against official Binance data.
    """
    if provider is None:
        provider = binance_provider

    expected_count = TIMEFRAME_MINUTES.get(timeframe, 1)
    duration_ms = expected_count * 60 * 1000
    window_end_time = window_start_time + duration_ms - 1

    # 1. Fetch internal 1m candles for the exact window from DB
    candles_1m = get_candles_1m(
        symbol=symbol,
        start_time=window_start_time,
        end_time=window_end_time,
        limit=expected_count + 10
    )

    constituent_count = len(candles_1m)
    
    # 2. Check completeness
    if constituent_count < expected_count:
        rec = ReconciliationRecord(
            symbol=symbol,
            timeframe=timeframe,
            open_time=window_start_time,
            close_time=window_end_time,
            status=ValidationStatus.INCOMPLETE,
            constituent_count=constituent_count,
            divergence_details=f"Missing 1m candles: found {constituent_count}/{expected_count}"
        )
        save_reconciliation(rec)
        return rec

    # 3. Aggregate internally
    aggs = aggregate_candles(candles_1m, timeframe, require_full_window=False)
    if not aggs:
        rec = ReconciliationRecord(
            symbol=symbol,
            timeframe=timeframe,
            open_time=window_start_time,
            close_time=window_end_time,
            status=ValidationStatus.ERROR,
            constituent_count=constituent_count,
            divergence_details="Failed to aggregate internal candles"
        )
        save_reconciliation(rec)
        return rec

    internal_agg = aggs[0]

    # 4. Fetch official candle from Binance public API
    try:
        official_candles = await provider.fetch_klines(
            symbol=symbol,
            interval=timeframe,
            start_time=window_start_time,
            end_time=window_start_time + 1000,
            limit=1
        )
    except Exception as e:
        logger.error("Error fetching official kline for reconciliation: %s", e)
        rec = ReconciliationRecord(
            symbol=symbol,
            timeframe=timeframe,
            open_time=window_start_time,
            close_time=window_end_time,
            status=ValidationStatus.ERROR,
            internal_open=internal_agg.open,
            internal_high=internal_agg.high,
            internal_low=internal_agg.low,
            internal_close=internal_agg.close,
            internal_volume=internal_agg.volume,
            constituent_count=constituent_count,
            divergence_details=f"Provider error: {e}"
        )
        save_reconciliation(rec)
        return rec

    if not official_candles:
        rec = ReconciliationRecord(
            symbol=symbol,
            timeframe=timeframe,
            open_time=window_start_time,
            close_time=window_end_time,
            status=ValidationStatus.PENDING,
            internal_open=internal_agg.open,
            internal_high=internal_agg.high,
            internal_low=internal_agg.low,
            internal_close=internal_agg.close,
            internal_volume=internal_agg.volume,
            constituent_count=constituent_count,
            divergence_details="Official candle not yet returned by exchange"
        )
        save_reconciliation(rec)
        return rec

    official = official_candles[0]

    # 5. Compare fields
    diffs = []
    if not is_close_enough(internal_agg.open, official.open, settings.PRICE_TOLERANCE_PCT):
        diffs.append(f"Open: internal={internal_agg.open} vs official={official.open}")
    if not is_close_enough(internal_agg.high, official.high, settings.PRICE_TOLERANCE_PCT):
        diffs.append(f"High: internal={internal_agg.high} vs official={official.high}")
    if not is_close_enough(internal_agg.low, official.low, settings.PRICE_TOLERANCE_PCT):
        diffs.append(f"Low: internal={internal_agg.low} vs official={official.low}")
    if not is_close_enough(internal_agg.close, official.close, settings.PRICE_TOLERANCE_PCT):
        diffs.append(f"Close: internal={internal_agg.close} vs official={official.close}")
    if not is_close_enough(internal_agg.volume, official.volume, settings.VOLUME_TOLERANCE_PCT):
        diffs.append(f"Volume: internal={internal_agg.volume} vs official={official.volume}")

    status = ValidationStatus.APPROVED if not diffs else ValidationStatus.DIVERGENT
    divergence_str = "; ".join(diffs) if diffs else None

    rec = ReconciliationRecord(
        symbol=symbol,
        timeframe=timeframe,
        open_time=window_start_time,
        close_time=window_end_time,
        status=status,
        internal_open=internal_agg.open,
        official_open=official.open,
        internal_high=internal_agg.high,
        official_high=official.high,
        internal_low=internal_agg.low,
        official_low=official.low,
        internal_close=internal_agg.close,
        official_close=official.close,
        internal_volume=internal_agg.volume,
        official_volume=official.volume,
        constituent_count=constituent_count,
        divergence_details=divergence_str
    )
    save_reconciliation(rec)
    return rec
