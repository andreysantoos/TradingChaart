import time
from typing import Optional
from fastapi import APIRouter, Query, HTTPException, BackgroundTasks
from pydantic import BaseModel

from app.core.config import settings
from app.models.schemas import Timeframe, SymbolInfo, HealthStatus, ValidationStatus
from app.providers.binance_futures import binance_provider
from app.db.database import (
    get_candles_1m,
    get_candles_agg,
    save_candles_agg,
    get_latest_1m_candle_time,
    get_reconciliations,
    get_stats,
    get_connection
)
from app.engine.aggregation import aggregate_candles, TIMEFRAME_MINUTES
from app.engine.reconciliation import reconcile_window
from app.services.backfill import backfill_symbol_history
from app.services.ingestion import ingestion_service

router = APIRouter()

# Cached symbols list
_cached_symbols: list[SymbolInfo] = []
_last_symbols_fetch: float = 0

@router.get("/markets/symbols", response_model=list[SymbolInfo])
async def list_symbols():
    global _cached_symbols, _last_symbols_fetch
    now = time.time()
    if not _cached_symbols or (now - _last_symbols_fetch > 300):
        symbols = await binance_provider.get_symbols()
        if symbols:
            _cached_symbols = symbols
            _last_symbols_fetch = now
    return _cached_symbols

@router.get("/candles")
async def get_candles(
    symbol: str = Query(..., description="e.g. BTCUSDT"),
    timeframe: Timeframe = Query(Timeframe.M1, description="Candle interval"),
    limit: int = Query(500, ge=10, le=1500),
    start_time: Optional[int] = None,
    end_time: Optional[int] = None,
    auto_backfill: bool = Query(True, description="Fetch from exchange if DB is empty")
):
    symbol = symbol.upper()
    tf_val = timeframe.value
    expected_minutes = TIMEFRAME_MINUTES.get(tf_val, 1)

    # 1. If timeframe is not 1m, check if we already have direct stored/backfilled aggregated candles
    if tf_val != "1m":
        direct_aggs = get_candles_agg(symbol=symbol, timeframe=tf_val, start_time=start_time, end_time=end_time, limit=limit)
        if len(direct_aggs) >= min(limit, 50):
            result = [
                {
                    "time": a["open_time"] // 1000,
                    "open": a["open"],
                    "high": a["high"],
                    "low": a["low"],
                    "close": a["close"],
                    "volume": a["volume"],
                    "quote_volume": a.get("quote_volume", 0.0),
                    "is_complete": bool(a.get("is_complete", 1)),
                    "constituent_count": a.get("constituent_count", 1)
                }
                for a in direct_aggs[-limit:]
            ]
            return {
                "symbol": symbol,
                "timeframe": tf_val,
                "count": len(result),
                "candles": result
            }

    # 2. Check local 1m candles
    candles_1m = get_candles_1m(symbol=symbol, start_time=start_time, end_time=end_time, limit=limit * expected_minutes)
    
    # 3. If DB has too few candles and auto_backfill is requested, backfill from exchange
    if len(candles_1m) < min(limit * expected_minutes, 100) and auto_backfill:
        await backfill_symbol_history(symbol=symbol, limit=1500, end_time=end_ms if 'end_ms' in locals() else end_time)
        ingestion_service.add_symbol(symbol)
        candles_1m = get_candles_1m(symbol=symbol, start_time=start_time, end_time=end_time, limit=limit * expected_minutes)

    # 4. Aggregate if timeframe > 1m
    if tf_val == "1m":
        result = [
            {
                "time": c.open_time // 1000,
                "open": c.open,
                "high": c.high,
                "low": c.low,
                "close": c.close,
                "volume": c.volume,
                "quote_volume": c.quote_volume
            }
            for c in candles_1m[-limit:]
        ]
    else:
        # Aggregate candles
        aggregated = aggregate_candles(candles_1m, tf_val, require_full_window=False)
        result = [
            {
                "time": a.open_time // 1000,
                "open": a.open,
                "high": a.high,
                "low": a.low,
                "close": a.close,
                "volume": a.volume,
                "quote_volume": a.quote_volume,
                "is_complete": a.is_complete,
                "constituent_count": a.constituent_count
            }
            for a in aggregated[-limit:]
        ]

    return {
        "symbol": symbol,
        "timeframe": tf_val,
        "count": len(result),
        "candles": result
    }

class SyncRequest(BaseModel):
    symbol: str
    limit: int = 1500

@router.post("/ingestion/sync")
async def trigger_sync(req: SyncRequest):
    symbol = req.symbol.upper()
    count = await backfill_symbol_history(symbol=symbol, limit=req.limit)
    ingestion_service.add_symbol(symbol)
    return {"symbol": symbol, "candles_added": count, "status": "synchronized"}

class ReconcileRequest(BaseModel):
    symbol: str
    timeframe: str
    window_start_time: int

@router.post("/reconciliation/run")
async def run_reconciliation(req: ReconcileRequest):
    rec = await reconcile_window(
        symbol=req.symbol.upper(),
        timeframe=req.timeframe,
        window_start_time=req.window_start_time
    )
    return rec

@router.get("/reconciliation/status")
async def reconciliation_status(
    symbol: Optional[str] = None,
    timeframe: Optional[str] = None,
    limit: int = 100
):
    records = get_reconciliations(symbol=symbol, timeframe=timeframe, limit=limit)
    return {"reconciliations": records}

@router.get("/health", response_model=HealthStatus)
async def health_check():
    stats = get_stats()
    now_ms = int(time.time() * 1000)
    max_t = stats["latest_open_time"]
    lag = int((now_ms - max_t) / 1000) if max_t else None

    return HealthStatus(
        status="healthy" if lag is not None and lag < 300 else "initializing",
        last_1m_candle_time=max_t,
        ingestion_lag_seconds=lag,
        active_symbols_tracked=list(ingestion_service.active_symbols),
        total_1m_candles_stored=stats["total_1m_candles"],
        reconciled_windows_count=stats["reconciled_windows"],
        divergent_count=stats["divergent_count"],
        incomplete_count=stats["incomplete_count"]
    )

class WatchlistUpdate(BaseModel):
    symbols: list[str]
    active_index: int = 0
    interval_seconds: int = 10

@router.get("/watchlist")
async def get_watchlist():
    conn = get_connection()
    row = conn.execute("SELECT * FROM watchlists WHERE id = 'default'").fetchone()
    conn.close()
    if row:
        import json
        symbols = json.loads(row["symbols_json"])
        return {
            "name": row["name"],
            "symbols": symbols,
            "active_index": row["active_index"],
            "interval_seconds": row["interval_seconds"]
        }
    return {
        "name": "default",
        "symbols": settings.DEFAULT_WATCHLIST,
        "active_index": 0,
        "interval_seconds": 10
    }

@router.post("/watchlist")
async def save_watchlist(req: WatchlistUpdate):
    import json
    now = int(time.time() * 1000)
    conn = get_connection()
    with conn:
        conn.execute("""
        INSERT OR REPLACE INTO watchlists (id, name, symbols_json, active_index, interval_seconds, updated_at)
        VALUES ('default', 'default', ?, ?, ?, ?)
        """, (json.dumps(req.symbols), req.active_index, req.interval_seconds, now))
    conn.close()
    ingestion_service.set_symbols(req.symbols)
    return {"status": "saved", "symbols": req.symbols}
