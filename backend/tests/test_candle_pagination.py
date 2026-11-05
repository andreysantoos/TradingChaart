import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.db.database import (
    init_db, save_candles_1m, save_candles_agg,
    get_candles_1m, get_candles_agg,
)
from app.main import app
from app.models.schemas import CandleRecord


@pytest.fixture
def history(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DATABASE_PATH", str(tmp_path / "history.db"))
    init_db()
    start = 1735689600000  # 2025-01-01 UTC
    records = [CandleRecord(
        symbol="ARPAUSDT", timeframe="1m",
        open_time=start + i * 60000, close_time=start + i * 60000 + 59999,
        open=0.01, high=0.012, low=0.009, close=0.011,
        volume=100, quote_volume=1.1, is_closed=True, origin="test",
    ) for i in range(674)]
    save_candles_1m(records)
    save_candles_agg([
        {**r.model_dump(), "timeframe": "1d",
         "open_time": start + i * 86400000,
         "close_time": start + (i + 1) * 86400000 - 1,
         "is_complete": True}
        for i, r in enumerate(records)
    ])
    return start


@pytest.mark.parametrize("timeframe,step", [("1m", 60000), ("1d", 86400000)])
def test_api_returns_latest_500_chronologically(history, timeframe, step):
    response = TestClient(app).get("/api/candles", params={
        "symbol": "ARPAUSDT", "timeframe": timeframe,
        "limit": 500, "auto_backfill": "false",
    })
    assert response.status_code == 200
    candles = response.json()["candles"]
    assert [c["time"] for c in candles] == [
        (history + i * step) // 1000 for i in range(174, 674)
    ]
    assert all(c["close"] == 0.011 for c in candles)


@pytest.mark.parametrize("timeframe,step", [("1m", 60000), ("1d", 86400000)])
def test_explicit_boundaries_preserve_pagination(history, timeframe, step):
    def read(**kwargs):
        if timeframe == "1m":
            return [c.open_time for c in get_candles_1m("ARPAUSDT", **kwargs)]
        return [c["open_time"] for c in get_candles_agg("ARPAUSDT", timeframe, **kwargs)]

    assert read(end_time=history + 100 * step, limit=10) == [
        history + i * step for i in range(91, 101)
    ]
    assert read(start_time=history + 20 * step, end_time=history + 100 * step, limit=10) == [
        history + i * step for i in range(20, 30)
    ]
    assert read(start_time=history + 700 * step, limit=10) == []
