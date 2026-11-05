import type { Candle, HealthData, SymbolInfo, Timeframe, WatchlistData } from '../types';

const API_BASE = '/api';

export async function getSymbols(): Promise<SymbolInfo[]> {
  const res = await fetch(`${API_BASE}/markets/symbols`);
  if (!res.ok) throw new Error(`Failed to fetch symbols: ${res.statusText}`);
  return res.json();
}

export async function getCandles(
  symbol: string,
  timeframe: Timeframe,
  limit = 500
): Promise<Candle[]> {
  const params = new URLSearchParams({
    symbol,
    timeframe,
    limit: limit.toString(),
    auto_backfill: 'true',
  });
  const res = await fetch(`${API_BASE}/candles?${params.toString()}`);
  if (!res.ok) throw new Error(`Failed to fetch candles: ${res.statusText}`);
  const data = await res.json();
  return data.candles;
}

export async function getHealth(): Promise<HealthData> {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) throw new Error(`Failed to fetch health: ${res.statusText}`);
  return res.json();
}

export async function getWatchlist(): Promise<WatchlistData> {
  const res = await fetch(`${API_BASE}/watchlist`);
  if (!res.ok) throw new Error(`Failed to fetch watchlist: ${res.statusText}`);
  return res.json();
}

export async function saveWatchlist(
  symbols: string[],
  activeIndex = 0,
  intervalSeconds = 10
): Promise<void> {
  await fetch(`${API_BASE}/watchlist`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      symbols,
      active_index: activeIndex,
      interval_seconds: intervalSeconds,
    }),
  });
}
