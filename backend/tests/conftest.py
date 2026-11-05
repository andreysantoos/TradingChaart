import pytest

from app.core.config import settings
from app.db.database import init_db


@pytest.fixture(autouse=True)
def isolated_database(tmp_path, monkeypatch):
    # Tests must never change the user's market database or watchlist.
    monkeypatch.setattr(settings, "DATABASE_PATH", str(tmp_path / "test.db"))
    init_db()
