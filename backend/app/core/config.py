import os
from pathlib import Path
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

class Settings(BaseModel):
    APP_NAME: str = "REA Trading Platform"
    APP_VERSION: str = "1.0.0"
    API_PREFIX: str = "/api"
    
    # Database
    DATABASE_PATH: str = str(DATA_DIR / "trading_platform.db")
    
    # Binance Futures
    BINANCE_FUTURES_BASE_URL: str = "https://fapi.binance.com"
    REQUEST_TIMEOUT_SECONDS: float = 10.0
    
    # Ingestion & Cadence
    INGESTION_INTERVAL_SECONDS: int = 60
    INGESTION_MARGIN_SECONDS: int = 2  # wait 2 seconds after minute close before fetching
    DEFAULT_WATCHLIST: list[str] = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT"]
    
    # Reconciliation tolerances (relative differences)
    PRICE_TOLERANCE_PCT: float = 0.0001  # 0.01% tolerance for floating-point / rounding
    VOLUME_TOLERANCE_PCT: float = 0.001   # 0.1% tolerance for volume aggregation differences

settings = Settings()
