export type Timeframe = '1m' | '5m' | '15m' | '30m' | '1h' | '4h' | '1d' | '1w';

export interface Candle {
  time: number; // UTC timestamp seconds
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  quote_volume?: number;
  is_complete?: boolean;
}

export interface SymbolInfo {
  symbol: string;
  base_asset: string;
  quote_asset: string;
  status: string;
  price_precision: number;
  quantity_precision: number;
}

export interface IndicatorConfig {
  id: string;
  name: string;
  enabled: boolean;
  type: 'overlay' | 'panel';
  params: Record<string, number | string>;
  color: string;
}

export interface WatchlistData {
  name: string;
  symbols: string[];
  active_index: number;
  interval_seconds: number;
}

export interface HealthData {
  status: string;
  last_1m_candle_time: number | null;
  ingestion_lag_seconds: number | null;
  active_symbols_tracked: string[];
  total_1m_candles_stored: number;
  reconciled_windows_count: number;
  divergent_count: number;
  incomplete_count: number;
}
