import asyncio
import logging
import time
from typing import Optional
from app.core.config import settings
from app.models.schemas import CandleRecord
from app.providers.binance_futures import BinanceFuturesProvider, binance_provider
from app.db.database import save_candles_1m, get_latest_1m_candle_time

logger = logging.getLogger(__name__)

class IngestionService:
    def __init__(self, provider: Optional[BinanceFuturesProvider] = None):
        self.provider = provider or binance_provider
        self.active_symbols: set[str] = set(settings.DEFAULT_WATCHLIST)
        self.is_running: bool = False
        self._task: Optional[asyncio.Task] = None
        self.last_run_timestamp: Optional[int] = None
        self.last_ingested_candle_time: Optional[int] = None

    def add_symbol(self, symbol: str):
        self.active_symbols.add(symbol.upper())

    def remove_symbol(self, symbol: str):
        self.active_symbols.discard(symbol.upper())

    def set_symbols(self, symbols: list[str]):
        self.active_symbols = {s.upper() for s in symbols}

    async def ingest_symbol(self, symbol: str):
        latest_time = get_latest_1m_candle_time(symbol)
        now_ms = int(time.time() * 1000)

        # If no local history, fetch recent 100 candles
        if latest_time is None:
            limit = 100
            start_time = None
        else:
            # Revisit the tail to finalize provisional or legacy imported candles
            start_time = latest_time  # Re-fetch the tail: older imports may contain an unfinished candle.
            # If already up to date within the current minute, nothing to fetch
            if start_time >= now_ms - 60000:
                return 0
            # Calculate missing candles count
            missing_count = (now_ms - start_time) // 60000
            limit = min(max(int(missing_count) + 5, 2), 500)

        candles = await self.provider.fetch_klines(
            symbol=symbol,
            interval="1m",
            start_time=start_time,
            limit=limit
        )

        if not candles:
            return 0

        # Filter out still unclosed candles (close_time > now_ms)
        closed_candles = [c for c in candles if c.is_closed and c.close_time < now_ms]
        if closed_candles:
            for c in closed_candles:
                c.origin = "ingestion"
            count = save_candles_1m(closed_candles)
            self.last_ingested_candle_time = max(c.open_time for c in closed_candles)
            return count
        return 0

    async def run_cycle(self):
        self.last_run_timestamp = int(time.time() * 1000)
        total_ingested = 0
        for symbol in list(self.active_symbols):
            try:
                count = await self.ingest_symbol(symbol)
                total_ingested += count
            except Exception as e:
                logger.error("Error in ingestion cycle for %s: %s", symbol, e)
        return total_ingested

    async def start(self):
        if self.is_running:
            return
        self.is_running = True
        logger.info("Starting background ingestion service for %d symbols...", len(self.active_symbols))
        
        while self.is_running:
            try:
                # Align with UTC minute boundary + margin
                now = time.time()
                seconds_in_minute = now % 60
                sleep_seconds = (60 - seconds_in_minute) + settings.INGESTION_MARGIN_SECONDS
                if sleep_seconds < 1:
                    sleep_seconds += 60

                await asyncio.sleep(sleep_seconds)
                if not self.is_running:
                    break
                await self.run_cycle()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Ingestion loop error: %s", e)
                await asyncio.sleep(5)

    def stop(self):
        self.is_running = False
        if self._task and not self._task.done():
            self._task.cancel()

ingestion_service = IngestionService()
