import asyncio
import importlib.util
from pathlib import Path
from unittest.mock import AsyncMock

import httpx

from app.api import routes
from app.db.database import get_candles_1m, get_candles_agg, save_candles_agg
from app.main import app
from app.models.schemas import CandleRecord
from app.providers.binance_futures import BinanceFuturesProvider
from app.services import chart_data
from app.services.chart_data import ChartDataService
from app.services.backfill import backfill_symbol_history

DAY = 86400000
START = 1793750400000  # 2026-11-04 UTC


def candle(start, price, interval='1d', duration=DAY):
    return CandleRecord(symbol='ARPAUSDT', timeframe=interval,
                        open_time=start, close_time=start + duration - 1,
                        open=price, high=price, low=price, close=price,
                        volume=123, quote_volume=1.23)


def test_refresh_replaces_legacy_open_candle_and_finalizes_at_rollover(monkeypatch):
    async def scenario():
        clock = [START + DAY // 2]
        monkeypatch.setattr(chart_data.time, 'time', lambda: clock[0] / 1000)
        stale = candle(START, .02)
        save_candles_agg([{**stale.model_dump(), 'is_complete': True}])
        provider = AsyncMock()
        provider.fetch_klines.return_value = [candle(START, .0101)]
        service = ChartDataService(provider)
        monkeypatch.setattr(routes, 'chart_data_service', service)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
            params = {'symbol': 'ARPAUSDT', 'timeframe': '1d', 'limit': 500}
            response = await client.get('/api/candles', params=params)
            assert response.status_code == 200
            assert response.json()['candles'][0]['close'] == .0101
            assert response.json()['candles'][0]['is_complete'] is False
            await client.get('/api/candles', params=params)
            assert provider.fetch_klines.await_count == 1
            clock[0] = START + DAY + 120000
            service._fresh.clear()
            provider.fetch_klines.return_value = [candle(START, .0102), candle(START + DAY, .0103)]
            response = await client.get('/api/candles', params=params)
            data = response.json()['candles']
            assert [c['close'] for c in data] == [.0102, .0103]
            assert [c['is_complete'] for c in data] == [True, False]
            assert len(get_candles_agg('ARPAUSDT', '1d')) == 2
            service._fresh.clear()
            provider.fetch_klines.return_value = []
            response = await client.get('/api/candles', params=params)
            assert response.status_code == 503
            assert not service._fresh
            assert len(get_candles_agg('ARPAUSDT', '1d')) == 2
    asyncio.run(scenario())


def test_concurrent_requests_download_once_and_expiry_refreshes(monkeypatch):
    async def scenario():
        ticks = [100.0]
        monkeypatch.setattr(chart_data.time, 'monotonic', lambda: ticks[0])
        provider = AsyncMock()
        provider.fetch_klines.return_value = [candle(START, .01)]
        service = ChartDataService(provider)
        await asyncio.gather(*(service.refresh('ARPAUSDT', '1d', 500) for _ in range(3)))
        assert provider.fetch_klines.await_count == 1
        ticks[0] += 61
        await service.refresh('ARPAUSDT', '1d', 500)
        assert provider.fetch_klines.await_count == 2
    asyncio.run(scenario())


def test_provider_and_backfill_do_not_finalize_open_minute(monkeypatch):
    async def scenario():
        monkeypatch.setattr(chart_data.time, 'time', lambda: (START + 90000) / 1000)
        rows = [[t, '.01', '.02', '.009', '.011', '100', t+59999, '1.1', 1]
                for t in [START, START+60000]]
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _: httpx.Response(200, json=rows)), base_url='https://test') as client:
            provider = BinanceFuturesProvider(client)
            candles = await provider.fetch_klines('ARPAUSDT')
            assert [c.is_closed for c in candles] == [True, False]
            await backfill_symbol_history('ARPAUSDT', provider=provider)
            assert len(get_candles_1m('ARPAUSDT')) == 1
            service = ChartDataService(provider)
            await service.refresh('ARPAUSDT', '1m', 500)
            assert [c.is_closed for c in get_candles_1m('ARPAUSDT')] == [True, False]
    asyncio.run(scenario())


def test_bulk_import_excludes_current_candle():
    path = Path(__file__).parents[1] / 'scripts' / 'download_bulk_history.py'
    spec = importlib.util.spec_from_file_location('bulk_history_test', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.rate_limiter.wait = AsyncMock()
    async def scenario():
        rows = [[t, '.01', '.02', '.009', '.011', '100', t+DAY-1, '1.1', 1]
                for t in [START, START+DAY]]
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _: httpx.Response(200, json=rows)), base_url='https://test') as client:
            result = await module.fetch_symbol_klines(client, 'ARPAUSDT', '1d', START, START+DAY+60000)
            assert [c['open_time'] for c in result] == [START]
    asyncio.run(scenario())


def test_ingestion_revisits_and_finalizes_legacy_tail(monkeypatch):
    from app.db.database import save_candles_1m
    from app.services.ingestion import IngestionService

    async def scenario():
        monkeypatch.setattr(chart_data.time, 'time', lambda: (START + 122000) / 1000)
        old = candle(START + 60000, .02, interval='1m', duration=60000)
        save_candles_1m([old])  # Legacy import incorrectly marked this snapshot closed.
        final = candle(START + 60000, .01, interval='1m', duration=60000)
        current = candle(START + 120000, .011, interval='1m', duration=60000)
        current.is_closed = False
        provider = AsyncMock()
        provider.fetch_klines.return_value = [final, current]
        assert await IngestionService(provider).ingest_symbol('ARPAUSDT') == 1
        assert provider.fetch_klines.call_args.kwargs['start_time'] == old.open_time
        records = get_candles_1m('ARPAUSDT')
        assert len(records) == 1
        assert records[0].close == .01
        assert records[0].is_closed
    asyncio.run(scenario())


def test_request_crossing_close_boundary_keeps_snapshot_provisional(monkeypatch):
    async def scenario():
        clock = [START + DAY - 500]
        monkeypatch.setattr(chart_data.time, 'time', lambda: clock[0] / 1000)
        async def response(_):
            clock[0] = START + DAY + 500
            return httpx.Response(200, json=[[
                START, '.01', '.02', '.009', '.011', '100', START+DAY-1, '1.1', 1
            ]])
        async with httpx.AsyncClient(transport=httpx.MockTransport(response), base_url='https://test') as client:
            service = ChartDataService(BinanceFuturesProvider(client))
            await service.refresh('ARPAUSDT', '1d', 500)
            assert not get_candles_agg('ARPAUSDT', '1d')[0]['is_complete']
    asyncio.run(scenario())
