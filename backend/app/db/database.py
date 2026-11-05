import sqlite3
import time
from typing import Optional
from app.core.config import settings
from app.models.schemas import CandleRecord, ReconciliationRecord, ValidationStatus

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(settings.DATABASE_PATH, timeout=30.0)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    with conn:
        # Canonical 1-minute candles table
        conn.execute("""
        CREATE TABLE IF NOT EXISTS candles_1m (
            provider TEXT NOT NULL,
            market TEXT NOT NULL,
            symbol TEXT NOT NULL,
            open_time INTEGER NOT NULL,
            close_time INTEGER NOT NULL,
            open REAL NOT NULL,
            high REAL NOT NULL,
            low REAL NOT NULL,
            close REAL NOT NULL,
            volume REAL NOT NULL,
            quote_volume REAL NOT NULL,
            trades_count INTEGER DEFAULT 0,
            is_closed INTEGER DEFAULT 1,
            origin TEXT NOT NULL,
            created_at INTEGER NOT NULL,
            PRIMARY KEY (provider, market, symbol, open_time)
        );
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_candles_1m_lookup ON candles_1m(symbol, open_time);")
        
        # Aggregated / Cached candles for multiple timeframes
        conn.execute("""
        CREATE TABLE IF NOT EXISTS candles_agg (
            provider TEXT NOT NULL,
            market TEXT NOT NULL,
            symbol TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            open_time INTEGER NOT NULL,
            close_time INTEGER NOT NULL,
            open REAL NOT NULL,
            high REAL NOT NULL,
            low REAL NOT NULL,
            close REAL NOT NULL,
            volume REAL NOT NULL,
            quote_volume REAL NOT NULL,
            constituent_count INTEGER NOT NULL,
            is_complete INTEGER NOT NULL,
            created_at INTEGER NOT NULL,
            PRIMARY KEY (provider, market, symbol, timeframe, open_time)
        );
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_candles_agg_lookup ON candles_agg(symbol, timeframe, open_time);")

        # Independent reconciliation ledger
        conn.execute("""
        CREATE TABLE IF NOT EXISTS reconciliations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            provider TEXT NOT NULL,
            market TEXT NOT NULL,
            symbol TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            open_time INTEGER NOT NULL,
            close_time INTEGER NOT NULL,
            status TEXT NOT NULL,
            internal_open REAL,
            official_open REAL,
            internal_high REAL,
            official_high REAL,
            internal_low REAL,
            official_low REAL,
            internal_close REAL,
            official_close REAL,
            internal_volume REAL,
            official_volume REAL,
            constituent_count INTEGER,
            divergence_details TEXT,
            verified_at INTEGER NOT NULL,
            UNIQUE(provider, market, symbol, timeframe, open_time)
        );
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_reconciliation_symbol_tf ON reconciliations(symbol, timeframe, open_time);")

        # Watchlists and user preferences
        conn.execute("""
        CREATE TABLE IF NOT EXISTS watchlists (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            symbols_json TEXT NOT NULL,
            active_index INTEGER DEFAULT 0,
            interval_seconds INTEGER DEFAULT 10,
            updated_at INTEGER NOT NULL
        );
        """)
    conn.close()

def save_candles_1m(candles: list[CandleRecord]) -> int:
    if not candles:
        return 0
    now = int(time.time() * 1000)
    conn = get_connection()
    with conn:
        cursor = conn.executemany("""
        INSERT OR REPLACE INTO candles_1m (
            provider, market, symbol, open_time, close_time,
            open, high, low, close, volume, quote_volume,
            trades_count, is_closed, origin, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            (
                c.provider, c.market, c.symbol, c.open_time, c.close_time,
                c.open, c.high, c.low, c.close, c.volume, c.quote_volume,
                c.trades_count, 1 if c.is_closed else 0, c.origin, now
            )
            for c in candles
        ])
        count = cursor.rowcount
    conn.close()
    return count

def get_candles_1m(symbol: str, start_time: Optional[int] = None, end_time: Optional[int] = None, limit: int = 1500) -> list[CandleRecord]:
    conn = get_connection()
    query = "SELECT * FROM candles_1m WHERE symbol = ?"
    params: list[object] = [symbol]
    
    if start_time is not None:
        query += " AND open_time >= ?"
        params.append(start_time)
    if end_time is not None:
        query += " AND open_time <= ?"
        params.append(end_time)
        
    # Without a start boundary, select the most recent page, then restore
    # chronological order for aggregation and chart consumers.
    order = "ASC" if start_time is not None else "DESC"
    query += f" ORDER BY open_time {order} LIMIT ?"
    params.append(limit)
    
    rows = conn.execute(query, params).fetchall()
    conn.close()
    if start_time is None:
        rows.reverse()
    
    return [
        CandleRecord(
            provider=r["provider"],
            market=r["market"],
            symbol=r["symbol"],
            timeframe="1m",
            open_time=r["open_time"],
            close_time=r["close_time"],
            open=r["open"],
            high=r["high"],
            low=r["low"],
            close=r["close"],
            volume=r["volume"],
            quote_volume=r["quote_volume"],
            trades_count=r["trades_count"],
            is_closed=bool(r["is_closed"]),
            origin=r["origin"]
        )
        for r in rows
    ]

def save_candles_agg(candles: list[dict]) -> int:
    if not candles:
        return 0
    now = int(time.time() * 1000)
    conn = get_connection()
    with conn:
        cursor = conn.executemany("""
        INSERT OR REPLACE INTO candles_agg (
            provider, market, symbol, timeframe, open_time, close_time,
            open, high, low, close, volume, quote_volume,
            constituent_count, is_complete, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            (
                c.get("provider", "binance"),
                c.get("market", "usds_m_futures"),
                c["symbol"],
                c["timeframe"],
                c["open_time"],
                c["close_time"],
                c["open"],
                c["high"],
                c["low"],
                c["close"],
                c["volume"],
                c.get("quote_volume", 0.0),
                c.get("constituent_count", 1),
                1 if c.get("is_complete", True) else 0,
                now
            )
            for c in candles
        ])
        count = cursor.rowcount
    conn.close()
    return count

def get_candles_agg(symbol: str, timeframe: str, start_time: Optional[int] = None, end_time: Optional[int] = None, limit: int = 1500) -> list[dict]:
    conn = get_connection()
    query = "SELECT * FROM candles_agg WHERE symbol = ? AND timeframe = ?"
    params: list[object] = [symbol, timeframe]
    if start_time is not None:
        query += " AND open_time >= ?"
        params.append(start_time)
    if end_time is not None:
        query += " AND open_time <= ?"
        params.append(end_time)
    order = "ASC" if start_time is not None else "DESC"
    query += f" ORDER BY open_time {order} LIMIT ?"
    params.append(limit)
    rows = conn.execute(query, params).fetchall()
    conn.close()
    if start_time is None:
        rows.reverse()
    return [dict(r) for r in rows]

def get_latest_1m_candle_time(symbol: str) -> Optional[int]:
    conn = get_connection()
    row = conn.execute(
        "SELECT MAX(open_time) as max_time FROM candles_1m WHERE symbol = ?", (symbol,)
    ).fetchone()
    conn.close()
    return row["max_time"] if row and row["max_time"] else None

def save_reconciliation(rec: ReconciliationRecord):
    now = int(time.time() * 1000)
    conn = get_connection()
    with conn:
        conn.execute("""
        INSERT OR REPLACE INTO reconciliations (
            provider, market, symbol, timeframe, open_time, close_time,
            status, internal_open, official_open, internal_high, official_high,
            internal_low, official_low, internal_close, official_close,
            internal_volume, official_volume, constituent_count, divergence_details, verified_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            rec.provider, rec.market, rec.symbol, rec.timeframe, rec.open_time, rec.close_time,
            rec.status.value, rec.internal_open, rec.official_open, rec.internal_high, rec.official_high,
            rec.internal_low, rec.official_low, rec.internal_close, rec.official_close,
            rec.internal_volume, rec.official_volume, rec.constituent_count, rec.divergence_details, now
        ))
    conn.close()

def get_reconciliations(symbol: Optional[str] = None, timeframe: Optional[str] = None, limit: int = 100) -> list[dict]:
    conn = get_connection()
    query = "SELECT * FROM reconciliations WHERE 1=1"
    params: list[object] = []
    if symbol:
        query += " AND symbol = ?"
        params.append(symbol)
    if timeframe:
        query += " AND timeframe = ?"
        params.append(timeframe)
    query += " ORDER BY open_time DESC LIMIT ?"
    params.append(limit)
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_stats() -> dict:
    conn = get_connection()
    c1 = conn.execute("SELECT COUNT(*) as cnt FROM candles_1m").fetchone()["cnt"]
    symbols = [r["symbol"] for r in conn.execute("SELECT DISTINCT symbol FROM candles_1m").fetchall()]
    max_time = conn.execute("SELECT MAX(open_time) as max_t FROM candles_1m").fetchone()["max_t"]
    reconciled = conn.execute("SELECT COUNT(*) as cnt FROM reconciliations").fetchone()["cnt"]
    divergent = conn.execute("SELECT COUNT(*) as cnt FROM reconciliations WHERE status = 'DIVERGENT'").fetchone()["cnt"]
    incomplete = conn.execute("SELECT COUNT(*) as cnt FROM reconciliations WHERE status = 'INCOMPLETE'").fetchone()["cnt"]
    conn.close()
    return {
        "total_1m_candles": c1,
        "symbols": symbols,
        "latest_open_time": max_time,
        "reconciled_windows": reconciled,
        "divergent_count": divergent,
        "incomplete_count": incomplete
    }
