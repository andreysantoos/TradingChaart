import argparse
import asyncio
from datetime import datetime, timezone
import logging
import sys
import time
from pathlib import Path

# Add backend to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

import httpx
from app.db.database import init_db, save_candles_agg, save_candles_1m
from app.models.schemas import CandleRecord
from app.providers.binance_futures import binance_provider

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("bulk_downloader")

BASE_URL = "https://fapi.binance.com"

# Timestamps
START_2025_MS = int(datetime(2025, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)
START_H2_2026_MS = int(datetime(2026, 7, 1, tzinfo=timezone.utc).timestamp() * 1000)

async def fetch_symbol_klines(
    client: httpx.AsyncClient,
    symbol: str,
    interval: str,
    start_time: int,
    end_time: int
) -> list[dict]:
    """Fetches klines in batches of 1500 from Binance REST API."""
    all_candles = []
    current_start = start_time
    
    while current_start < end_time:
        params = {
            "symbol": symbol,
            "interval": interval,
            "startTime": current_start,
            "endTime": end_time,
            "limit": 1500
        }
        for attempt in range(3):
            try:
                resp = await client.get("/fapi/v1/klines", params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    if not data:
                        return all_candles
                    
                    for k in data:
                        all_candles.append({
                            "provider": "binance",
                            "market": "usds_m_futures",
                            "symbol": symbol,
                            "timeframe": interval,
                            "open_time": int(k[0]),
                            "close_time": int(k[6]),
                            "open": float(k[1]),
                            "high": float(k[2]),
                            "low": float(k[3]),
                            "close": float(k[4]),
                            "volume": float(k[5]),
                            "quote_volume": float(k[7]),
                            "constituent_count": 1,
                            "is_complete": True
                        })
                    
                    last_open = int(data[-1][0])
                    if len(data) < 1500 or last_open <= current_start:
                        return all_candles
                    current_start = last_open + 1
                    break
                elif resp.status_code == 429:
                    wait_s = int(resp.headers.get("Retry-After", 2))
                    await asyncio.sleep(wait_s)
                else:
                    await asyncio.sleep(1)
            except Exception as e:
                await asyncio.sleep(1)
    return all_candles

async def process_symbol_tier(
    semaphore: asyncio.Semaphore,
    client: httpx.AsyncClient,
    symbol: str,
    interval: str,
    start_time: int,
    end_time: int,
    is_1m: bool = False
):
    async with semaphore:
        candles = await fetch_symbol_klines(client, symbol, interval, start_time, end_time)
        if not candles:
            return 0
        
        if is_1m:
            records = [
                CandleRecord(
                    provider=c["provider"],
                    market=c["market"],
                    symbol=c["symbol"],
                    timeframe="1m",
                    open_time=c["open_time"],
                    close_time=c["close_time"],
                    open=c["open"],
                    high=c["high"],
                    low=c["low"],
                    close=c["close"],
                    volume=c["volume"],
                    quote_volume=c["quote_volume"],
                    is_closed=True,
                    origin="bulk_history"
                )
                for c in candles
            ]
            count = save_candles_1m(records)
        else:
            count = save_candles_agg(candles)
        return count

async def run_tier(
    symbols: list[str],
    tier_name: str,
    intervals: list[str],
    start_time: int,
    end_time: int,
    concurrency: int = 10
):
    print(f"\n=======================================================")
    print(f" Iniciando {tier_name} ({', '.join(intervals)}) para {len(symbols)} ativos")
    print(f" De: {datetime.fromtimestamp(start_time/1000, tz=timezone.utc)} até {datetime.fromtimestamp(end_time/1000, tz=timezone.utc)}")
    print(f"=======================================================")

    semaphore = asyncio.Semaphore(concurrency)
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=15.0) as client:
        for interval in intervals:
            is_1m = (interval == "1m")
            t0 = time.time()
            total_candles = 0
            tasks = [
                process_symbol_tier(semaphore, client, sym, interval, start_time, end_time, is_1m)
                for sym in symbols
            ]
            
            for idx, fut in enumerate(asyncio.as_completed(tasks), 1):
                cnt = await fut
                total_candles += cnt
                if idx % 25 == 0 or idx == len(symbols):
                    elapsed = time.time() - t0
                    print(f"  [{interval}] Progresso: {idx}/{len(symbols)} ativos processados | {total_candles} velas salvas ({elapsed:.1f}s)")

async def main():
    parser = argparse.ArgumentParser(description="REA Top-Down Bulk Ingestion")
    parser.add_argument("--tier", default="macro", choices=["macro", "intermediate", "intraday", "recent", "all"], help="Tier to download")
    parser.add_argument("--symbols", default="all", help="Comma-separated symbols or 'all'")
    parser.add_argument("--concurrency", type=int, default=15, help="Concurrent workers")
    args = parser.parse_args()

    init_db()

    # Discover symbols
    print("Descobrindo contratos perpétuos USDT ativos...")
    all_sym_info = await binance_provider.get_symbols()
    all_symbols = [s.symbol for s in all_sym_info]
    print(f"Total descoberto: {len(all_symbols)} contratos.")

    if args.symbols.lower() != "all":
        selected = [s.strip().upper() for s in args.symbols.split(",")]
        symbols = [s for s in selected if s in all_symbols]
    else:
        symbols = all_symbols

    now_ms = int(time.time() * 1000)

    # Tier 1: Macro (1w, 1d) 2025 to now
    if args.tier in ["macro", "all"]:
        await run_tier(symbols, "Tier 1: Macro", ["1w", "1d"], START_2025_MS, now_ms, args.concurrency)

    # Tier 2: Intermediate (4h, 1h) 2025 to now
    if args.tier in ["intermediate", "all"]:
        await run_tier(symbols, "Tier 2: Intermediário", ["4h", "1h"], START_2025_MS, now_ms, args.concurrency)

    # Tier 3: Intraday (15m) 2025 to now
    if args.tier in ["intraday", "all"]:
        await run_tier(symbols, "Tier 3: Intraday (15m)", ["15m"], START_2025_MS, now_ms, args.concurrency)

    # Tier 4: Recent Sub-15m (1m, 5m) H2 2026 to now
    if args.tier in ["recent", "all"]:
        await run_tier(symbols, "Tier 4: Granularidade Alta Recente (5m, 1m)", ["5m", "1m"], START_H2_2026_MS, now_ms, args.concurrency)

    print("\nExecução de ingestão finalizada com sucesso.")

if __name__ == "__main__":
    asyncio.run(main())
