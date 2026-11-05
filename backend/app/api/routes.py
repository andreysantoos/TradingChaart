import time
from typing import Optional
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel

from app.core.config import settings
from app.models.schemas import Timeframe, SymbolInfo, HealthStatus
from app.providers.binance_futures import binance_provider
from app.db.database import (
    get_candles_1m,
    get_candles_agg,
    get_reconciliations,
    get_stats,
    get_connection
)
from app.engine.reconciliation import reconcile_window
from app.services.backfill import backfill_symbol_history
from app.services.ingestion import ingestion_service
from app.services.chart_data import chart_data_service

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
    auto_backfill: bool = Query(True, description="Refresh official candles in the backend (60s cache); false reads local data only")
):
    symbol = symbol.upper()
    tf_val = timeframe.value
    # Imported higher timeframes are official candles, maintained independently
    # from canonical 1m ingestion. Never build a daily candle from partial history.
    if auto_backfill:
        try:
            await chart_data_service.refresh(symbol, tf_val, limit, start_time, end_time)
        except (RuntimeError, ValueError) as exc:
            raise HTTPException(status_code=503, detail="Não foi possível atualizar os candles na Binance. Tente novamente.") from exc

    now_ms = int(time.time() * 1000)
    if tf_val == "1m":
        rows = [c.model_dump() for c in get_candles_1m(
            symbol, start_time=start_time, end_time=end_time, limit=limit
        )]
    else:
        rows = get_candles_agg(symbol, tf_val, start_time=start_time, end_time=end_time, limit=limit)

    result = [{
        "time": r["open_time"] // 1000,
        "open": r["open"], "high": r["high"], "low": r["low"],
        "close": r["close"], "volume": r["volume"],
        "quote_volume": r.get("quote_volume", 0.0),
        "is_complete": bool(r.get("is_complete", r.get("is_closed", False))) and r["close_time"] < now_ms,
    } for r in rows]
    return {"symbol": symbol, "timeframe": tf_val, "count": len(result), "candles": result}

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
