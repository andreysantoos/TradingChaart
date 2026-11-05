import argparse
import asyncio
from datetime import datetime, timezone
import sys
from pathlib import Path

# Add backend to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.db.database import init_db, get_candles_1m, get_reconciliations
from app.engine.aggregation import TIMEFRAME_MINUTES, get_window_start_time
from app.engine.reconciliation import reconcile_window
from app.services.backfill import backfill_symbol_history
from app.providers.binance_futures import binance_provider

def parse_iso_or_ts(val: str) -> int:
    try:
        # Check if already timestamp in ms
        return int(val)
    except ValueError:
        # Parse ISO date YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS
        dt = datetime.fromisoformat(val)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.timestamp() * 1000)

async def main():
    parser = argparse.ArgumentParser(description="REA Independent Data Validation and Audit Script")
    parser.add_argument("--symbol", default="BTCUSDT", help="Trading pair symbol (default: BTCUSDT)")
    parser.add_argument("--interval", "--timeframe", default="15m", choices=["5m", "15m", "30m", "1h", "4h", "1d"], help="Target timeframe")
    parser.add_argument("--from", dest="from_date", required=True, help="Start time (ISO 8601 or ms timestamp)")
    parser.add_argument("--to", dest="to_date", required=True, help="End time (ISO 8601 or ms timestamp)")
    parser.add_argument("--auto-backfill", action="store_true", default=True, help="Backfill missing 1m data if needed")

    args = parser.parse_args()
    init_db()

    symbol = args.symbol.upper()
    timeframe = args.interval
    start_ms = parse_iso_or_ts(args.from_date)
    end_ms = parse_iso_or_ts(args.to_date)

    minutes = TIMEFRAME_MINUTES[timeframe]
    duration_ms = minutes * 60 * 1000

    print(f"=== Starting Audit for {symbol} [{timeframe}] ===")
    print(f"Range: {datetime.fromtimestamp(start_ms/1000, tz=timezone.utc)} to {datetime.fromtimestamp(end_ms/1000, tz=timezone.utc)}")

    # Check if 1m data exists, if not backfill
    local_1m = get_candles_1m(symbol=symbol, start_time=start_ms, end_time=end_ms, limit=50000)
    if not local_1m and args.auto_backfill:
        print(f"No local 1m data found in range. Backfilling from Binance...")
        await backfill_symbol_history(symbol=symbol, limit=1500, end_time=end_ms)
        local_1m = get_candles_1m(symbol=symbol, start_time=start_ms, end_time=end_ms, limit=50000)

    # Compute expected window starts
    first_window = get_window_start_time(start_ms, timeframe)
    current_window = first_window
    windows_to_check: list[int] = []
    while current_window < end_ms:
        windows_to_check.append(current_window)
        current_window += duration_ms

    print(f"Identified {len(windows_to_check)} windows to audit.")
    
    results = {"APPROVED": 0, "DIVERGENT": 0, "INCOMPLETE": 0, "PENDING": 0, "ERROR": 0}

    for w_start in windows_to_check:
        rec = await reconcile_window(symbol, timeframe, w_start)
        status = rec.status.value
        results[status] = results.get(status, 0) + 1
        dt_str = datetime.fromtimestamp(w_start / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        
        if status == "APPROVED":
            print(f"[{status}] Window {dt_str}: OK (internal={rec.internal_close} / official={rec.official_close})")
        else:
            print(f"[{status}] Window {dt_str}: {rec.divergence_details}")

    print("\n=== Audit Summary ===")
    print(f"Total windows: {len(windows_to_check)}")
    for status, count in results.items():
        print(f"  {status}: {count}")

    await binance_provider.close()

if __name__ == "__main__":
    asyncio.run(main())
