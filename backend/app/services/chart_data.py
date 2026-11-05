"""Refresh the requested official timeframe in the backend, before serving it."""
import asyncio
import time

from app.db.database import save_candles_1m, save_candles_agg
from app.providers.binance_futures import binance_provider


class ChartDataService:
    def __init__(self, provider=None):
        self.provider = provider or binance_provider
        self._fresh = {}
        # Serialize refreshes to avoid duplicate downloads and API bursts.
        self._lock = asyncio.Lock()

    async def refresh(self, symbol, timeframe, limit, start_time=None, end_time=None):
        key = (symbol, timeframe, limit, start_time, end_time)
        async with self._lock:
            now = time.monotonic()
            self._fresh = {k: expiry for k, expiry in self._fresh.items() if expiry > now}
            if key in self._fresh:
                return
            requested_at_ms = int(time.time() * 1000)
            candles = await self.provider.fetch_klines(
                symbol=symbol, interval=timeframe, limit=limit,
                start_time=start_time, end_time=end_time,
            )
            if not candles:
                raise RuntimeError("Provider returned no candles; cache was not refreshed")
            if timeframe == "1m":
                # The current minute is provisional and will be replaced on refresh.
                for c in candles:
                    c.is_closed = c.is_closed and c.close_time < requested_at_ms
                save_candles_1m(candles)
            else:
                save_candles_agg([
                    {**c.model_dump(), "is_complete": c.is_closed and c.close_time < requested_at_ms,
                     "constituent_count": 1}
                    for c in candles
                ])
            self._fresh[key] = time.monotonic() + 60


chart_data_service = ChartDataService()
