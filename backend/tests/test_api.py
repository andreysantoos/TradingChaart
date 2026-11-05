import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.database import init_db

@pytest.fixture(autouse=True)
def setup_database():
    init_db()

def test_root_endpoint():
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"

def test_watchlist_endpoint():
    client = TestClient(app)
    response = client.get("/api/watchlist")
    assert response.status_code == 200
    data = response.json()
    assert "symbols" in data
    assert len(data["symbols"]) > 0

    # Test update watchlist
    update_resp = client.post("/api/watchlist", json={
        "symbols": ["BTCUSDT", "ETHUSDT"],
        "active_index": 0,
        "interval_seconds": 15
    })
    assert update_resp.status_code == 200
    assert update_resp.json()["symbols"] == ["BTCUSDT", "ETHUSDT"]

def test_health_endpoint():
    client = TestClient(app)
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert "total_1m_candles_stored" in data
