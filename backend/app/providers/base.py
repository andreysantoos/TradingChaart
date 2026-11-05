from abc import ABC, abstractmethod
from typing import Optional
from app.models.schemas import CandleRecord, SymbolInfo

class MarketDataProvider(ABC):
    provider_id: str
    market_id: str

    @abstractmethod
    async def get_symbols(self) -> list[SymbolInfo]:
        """Discover and list tradable instruments."""
        pass

    @abstractmethod
    async def fetch_klines(
        self,
        symbol: str,
        interval: str,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        limit: int = 500
    ) -> list[CandleRecord]:
        """Fetch canonical OHLCV candles from official public REST endpoints."""
        pass
