import logging
import time
from typing import Optional
from app.models.schemas import CandleRecord
from app.providers.binance_futures import BinanceFuturesProvider, binance_provider
from app.db.database import save_candles_1m, get_candles_1m, get_latest_1m_candle_time

logger = logging.getLogger(__name__)

async def backfill_symbol_history(
    symbol: str,
    limit: int = 1500,
    end_time: Optional[int] = None,
    provider: Optional[BinanceFuturesProvider] = None
) -> int:
    """
    Downloads historical 1m candles for a symbol and persists them into canonical storage.
    """
    if provider is None:
        provider = binance_provider

    if end_time is None:
        end_time = int(time.time() * 1000)

    logger.info("Starting historical backfill for %s (limit: %d)...", symbol, limit)
    
    # Binance klines returns up to 1500 per call
    batch_size = min(limit, 1500)
    total_inserted = 0

    try:
        candles = await provider.fetch_klines(
            symbol=symbol,
            interval="1m",
            end_time=end_time,
            limit=batch_size
        )
        if candles:
            # Mark origin as backfill
            for c in candles:
                c.origin = "backfill"
            count = save_candles_1m(candles)
            total_inserted += count
            logger.info("Successfully backfilled %d 1m candles for %s", count, symbol)
    except Exception as e:
        logger.error("Failed backfilling for %s: %s", symbol, e)

    return total_inserted
