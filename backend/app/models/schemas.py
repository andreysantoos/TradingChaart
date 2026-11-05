from enum import Enum
from typing import Optional, Any
from pydantic import BaseModel, Field

class Timeframe(str, Enum):
    M1 = "1m"
    M5 = "5m"
    M15 = "15m"
    M30 = "30m"
    H1 = "1h"
    H4 = "4h"
    D1 = "1d"
    W1 = "1w"

class ValidationStatus(str, Enum):
    APPROVED = "APPROVED"
    DIVERGENT = "DIVERGENT"
    INCOMPLETE = "INCOMPLETE"
    PENDING = "PENDING"
    ERROR = "ERROR"

class CandleRecord(BaseModel):
    provider: str = "binance"
    market: str = "usds_m_futures"
    symbol: str
    timeframe: str = "1m"
    open_time: int  # timestamp ms UTC
    close_time: int # timestamp ms UTC
    open: float
    high: float
    low: float
    close: float
    volume: float
    quote_volume: Optional[float] = 0.0
    trades_count: Optional[int] = 0
    is_closed: bool = True
    origin: str = "ingestion"  # "ingestion", "backfill", "aggregated", "official"

class AggregatedCandle(BaseModel):
    symbol: str
    timeframe: str
    open_time: int
    close_time: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    quote_volume: float
    constituent_count: int
    expected_count: int
    is_complete: bool

class ReconciliationRecord(BaseModel):
    id: Optional[int] = None
    provider: str = "binance"
    market: str = "usds_m_futures"
    symbol: str
    timeframe: str
    open_time: int
    close_time: int
    status: ValidationStatus
    internal_open: Optional[float] = None
    official_open: Optional[float] = None
    internal_high: Optional[float] = None
    official_high: Optional[float] = None
    internal_low: Optional[float] = None
    official_low: Optional[float] = None
    internal_close: Optional[float] = None
    official_close: Optional[float] = None
    internal_volume: Optional[float] = None
    official_volume: Optional[float] = None
    constituent_count: Optional[int] = None
    divergence_details: Optional[str] = None
    verified_at: Optional[int] = None

class SymbolInfo(BaseModel):
    symbol: str
    base_asset: str
    quote_asset: str
    status: str
    price_precision: int
    quantity_precision: int

class WatchlistModel(BaseModel):
    name: str = "default"
    symbols: list[str] = Field(default_factory=list)
    active_index: int = 0
    interval_seconds: int = 10

class IndicatorConfig(BaseModel):
    id: str
    name: str
    type: str  # overlay or panel
    enabled: bool = False
    params: dict[str, Any] = Field(default_factory=dict)
    color: Optional[str] = "#2962FF"

class HealthStatus(BaseModel):
    status: str
    last_1m_candle_time: Optional[int] = None
    ingestion_lag_seconds: Optional[int] = None
    active_symbols_tracked: list[str] = Field(default_factory=list)
    total_1m_candles_stored: int = 0
    reconciled_windows_count: int = 0
    divergent_count: int = 0
    incomplete_count: int = 0
