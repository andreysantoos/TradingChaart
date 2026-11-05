import asyncio
import logging
from typing import Optional
import httpx
from app.core.config import settings
from app.models.schemas import CandleRecord, SymbolInfo
from app.providers.base import MarketDataProvider

logger = logging.getLogger(__name__)

class BinanceFuturesProvider(MarketDataProvider):
    provider_id: str = "binance"
    market_id: str = "usds_m_futures"
    base_url: str = settings.BINANCE_FUTURES_BASE_URL

    def __init__(self, client: Optional[httpx.AsyncClient] = None):
        self._client = client

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=settings.REQUEST_TIMEOUT_SECONDS,
                headers={"User-Agent": "REA-TradingPlatform/1.0"}
            )
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def get_symbols(self) -> list[SymbolInfo]:
        client = await self._get_client()
        url = "/fapi/v1/exchangeInfo"
        
        for attempt in range(3):
            try:
                resp = await client.get(url)
                if resp.status_code == 200:
                    data = resp.json()
                    symbols = []
                    for item in data.get("symbols", []):
                        # Filter for active perpetual contracts against USDT
                        if item.get("status") == "TRADING" and item.get("contractType") == "PERPETUAL":
                            symbols.append(
                                SymbolInfo(
                                    symbol=item["symbol"],
                                    base_asset=item["baseAsset"],
                                    quote_asset=item["quoteAsset"],
                                    status=item["status"],
                                    price_precision=item.get("pricePrecision", 2),
                                    quantity_precision=item.get("quantityPrecision", 3)
                                )
                            )
                    return symbols
                elif resp.status_code == 429:
                    wait_time = int(resp.headers.get("Retry-After", 2))
                    logger.warning("Binance rate limit hit, backing off for %ds", wait_time)
                    await asyncio.sleep(wait_time)
                else:
                    logger.error("Binance exchangeInfo error %d: %s", resp.status_code, resp.text)
                    await asyncio.sleep(1 * (attempt + 1))
            except Exception as e:
                logger.error("Failed to fetch exchangeInfo (attempt %d): %s", attempt + 1, e)
                await asyncio.sleep(1 * (attempt + 1))
        return []

    async def fetch_klines(
        self,
        symbol: str,
        interval: str = "1m",
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        limit: int = 500
    ) -> list[CandleRecord]:
        client = await self._get_client()
        url = "/fapi/v1/klines"
        params: dict[str, str | int] = {
            "symbol": symbol.upper(),
            "interval": interval,
            "limit": min(limit, 1500)
        }
        if start_time is not None:
            params["startTime"] = start_time
        if end_time is not None:
            params["endTime"] = end_time

        for attempt in range(3):
            try:
                resp = await client.get(url, params=params)
                if resp.status_code == 200:
                    raw_candles = resp.json()
                    result: list[CandleRecord] = []
                    for k in raw_candles:
                        # k format: [open_time, open, high, low, close, volume, close_time, quote_vol, trades, ...]
                        open_time = int(k[0])
                        close_time = int(k[6])
                        open_p = float(k[1])
                        high_p = float(k[2])
                        low_p = float(k[3])
                        close_p = float(k[4])
                        volume = float(k[5])
                        quote_volume = float(k[7])
                        trades = int(k[8])

                        result.append(
                            CandleRecord(
                                provider=self.provider_id,
                                market=self.market_id,
                                symbol=symbol.upper(),
                                timeframe=interval,
                                open_time=open_time,
                                close_time=close_time,
                                open=open_p,
                                high=high_p,
                                low=low_p,
                                close=close_p,
                                volume=volume,
                                quote_volume=quote_volume,
                                trades_count=trades,
                                is_closed=True,
                                origin="official"
                            )
                        )
                    return result
                elif resp.status_code == 429:
                    wait_time = int(resp.headers.get("Retry-After", 2))
                    logger.warning("Binance rate limit hit, sleeping %ds", wait_time)
                    await asyncio.sleep(wait_time)
                else:
                    logger.error("Binance klines error %d: %s", resp.status_code, resp.text)
                    await asyncio.sleep(1 * (attempt + 1))
            except Exception as e:
                logger.error("Error fetching klines for %s (attempt %d): %s", symbol, attempt + 1, e)
                await asyncio.sleep(1 * (attempt + 1))
        return []

binance_provider = BinanceFuturesProvider()
