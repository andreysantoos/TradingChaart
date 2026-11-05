import { useEffect, useState, useRef, useCallback } from 'react';
import { Header } from './components/Header';
import { ChartContainer } from './components/ChartContainer';
import { WatchlistDrawer } from './components/WatchlistDrawer';
import { IndicatorsModal } from './components/IndicatorsModal';
import type { Candle, HealthData, IndicatorConfig, SymbolInfo, Timeframe } from './types';
import { getCandles, getHealth, getSymbols, getWatchlist, saveWatchlist } from './services/api';
import './App.css';

const DEFAULT_INDICATORS: IndicatorConfig[] = [
  {
    id: 'sma',
    name: 'SMA (Média Móvel Simples)',
    enabled: true,
    type: 'overlay',
    params: { period: 20 },
    color: '#f7931a',
  },
  {
    id: 'ema',
    name: 'EMA (Média Móvel Exponencial)',
    enabled: true,
    type: 'overlay',
    params: { period: 9 },
    color: '#2962ff',
  },
  {
    id: 'bollinger',
    name: 'Bandas de Bollinger',
    enabled: false,
    type: 'overlay',
    params: { period: 20, stdDev: 2 },
    color: '#ab47bc',
  },
  {
    id: 'rsi',
    name: 'RSI (Índice de Força Relativa)',
    enabled: false,
    type: 'panel',
    params: { period: 14 },
    color: '#e91e63',
  },
  {
    id: 'macd',
    name: 'MACD',
    enabled: false,
    type: 'panel',
    params: { fast: 12, slow: 26, signal: 9 },
    color: '#2962ff',
  },
];

export function App() {
  const [symbols, setSymbols] = useState<SymbolInfo[]>([]);
  const [currentSymbol, setCurrentSymbol] = useState<string>('BTCUSDT');
  const [timeframe, setTimeframe] = useState<Timeframe>('15m');
  const [isLogScale, setIsLogScale] = useState<boolean>(false);
  
  // Watchlist & Rotation
  const [watchlist, setWatchlist] = useState<string[]>([
    'BTCUSDT',
    'ETHUSDT',
    'SOLUSDT',
    'BNBUSDT',
    'XRPUSDT',
  ]);
  const [activeWatchlistIndex, setActiveWatchlistIndex] = useState<number>(0);
  const [rotationInterval, setRotationInterval] = useState<number>(10);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [timerProgress, setTimerProgress] = useState<number>(0);

  // Indicators
  const [indicators, setIndicators] = useState<IndicatorConfig[]>(DEFAULT_INDICATORS);

  // Candles & Loading
  const [candles, setCandles] = useState<Candle[]>([]);
  const [isLoadingCandles, setIsLoadingCandles] = useState<boolean>(false);

  // Modals & Drawers
  const [isWatchlistOpen, setIsWatchlistOpen] = useState<boolean>(false);
  const [isIndicatorsOpen, setIsIndicatorsOpen] = useState<boolean>(false);

  // Health
  const [health, setHealth] = useState<HealthData | null>(null);

  // Memory Cache for smooth rotation without re-requesting if fresh
  const candlesCache = useRef<Map<string, { candles: Candle[]; ts: number }>>(new Map());

  // Initial load: symbols, default watchlist, health
  useEffect(() => {
    getSymbols().then(setSymbols).catch(console.error);
    getWatchlist()
      .then((data) => {
        if (data.symbols && data.symbols.length > 0) {
          setWatchlist(data.symbols);
          setRotationInterval(data.interval_seconds || 10);
        }
      })
      .catch(console.error);

    getHealth().then(setHealth).catch(console.error);
    const healthInterval = setInterval(() => {
      getHealth().then(setHealth).catch(console.error);
    }, 15000);

    return () => clearInterval(healthInterval);
  }, []);

  // Fetch candles when symbol or timeframe changes
  const loadCandles = useCallback(
    async (sym: string, tf: Timeframe) => {
      const cacheKey = `${sym}_${tf}`;
      const cached = candlesCache.current.get(cacheKey);
      const now = Date.now();

      if (cached && now - cached.ts < 30000) {
        setCandles(cached.candles);
        return;
      }

      setIsLoadingCandles(true);
      try {
        const data = await getCandles(sym, tf, 500);
        setCandles(data);
        candlesCache.current.set(cacheKey, { candles: data, ts: Date.now() });
      } catch (err) {
        console.error('Failed to load candles:', err);
      } finally {
        setIsLoadingCandles(false);
      }
    },
    []
  );

  useEffect(() => {
    loadCandles(currentSymbol, timeframe);
  }, [currentSymbol, timeframe, loadCandles]);

  // Robust Auto-Rotation Loop
  useEffect(() => {
    if (!isPlaying || watchlist.length === 0) {
      setTimerProgress(0);
      return;
    }

    const intervalMs = rotationInterval * 1000;
    const tickMs = 100;
    let elapsed = 0;

    const timer = setInterval(() => {
      elapsed += tickMs;
      const progress = Math.min((elapsed / intervalMs) * 100, 100);
      setTimerProgress(progress);

      if (elapsed >= intervalMs) {
        elapsed = 0;
        setTimerProgress(0);

        setActiveWatchlistIndex((prevIndex) => {
          const nextIndex = (prevIndex + 1) % watchlist.length;
          const nextSymbol = watchlist[nextIndex];
          setCurrentSymbol(nextSymbol);
          return nextIndex;
        });
      }
    }, tickMs);

    return () => {
      clearInterval(timer);
    };
  }, [isPlaying, rotationInterval, watchlist]);

  // Manual select symbol
  const handleSelectSymbol = (sym: string) => {
    setCurrentSymbol(sym);
    const idx = watchlist.indexOf(sym);
    if (idx !== -1) {
      setActiveWatchlistIndex(idx);
    }
  };

  // Toggle Play / Pause
  const handleTogglePlay = () => {
    setIsPlaying((prev) => !prev);
  };

  const handleStopPlay = () => {
    setIsPlaying(false);
    setTimerProgress(0);
  };

  // Update Watchlist
  const handleUpdateWatchlist = (newList: string[]) => {
    setWatchlist(newList);
    saveWatchlist(newList, activeWatchlistIndex, rotationInterval);
  };

  // Indicator controls
  const handleToggleIndicator = (id: string) => {
    setIndicators((prev) =>
      prev.map((ind) => (ind.id === id ? { ...ind, enabled: !ind.enabled } : ind))
    );
  };

  const handleUpdateIndicatorParams = (id: string, params: Record<string, number | string>) => {
    setIndicators((prev) =>
      prev.map((ind) => (ind.id === id ? { ...ind, params } : ind))
    );
  };

  return (
    <div className="app-container">
      <Header
        currentSymbol={currentSymbol}
        onSelectSymbol={handleSelectSymbol}
        symbols={symbols}
        timeframe={timeframe}
        onSelectTimeframe={setTimeframe}
        isLogScale={isLogScale}
        onToggleScale={() => setIsLogScale((prev) => !prev)}
        isPlaying={isPlaying}
        onTogglePlay={handleTogglePlay}
        onStopPlay={handleStopPlay}
        rotationInterval={rotationInterval}
        onChangeInterval={setRotationInterval}
        watchlistLength={watchlist.length}
        activeWatchlistIndex={activeWatchlistIndex}
        timerProgress={timerProgress}
        onOpenIndicators={() => setIsIndicatorsOpen(true)}
        onOpenWatchlist={() => setIsWatchlistOpen(true)}
        health={health}
      />

      <main className="main-content">
        <ChartContainer
          symbol={currentSymbol}
          timeframe={timeframe}
          candles={candles}
          isLogScale={isLogScale}
          indicators={indicators}
          isLoading={isLoadingCandles}
        />
      </main>

      <WatchlistDrawer
        isOpen={isWatchlistOpen}
        onClose={() => setIsWatchlistOpen(false)}
        watchlist={watchlist}
        currentSymbol={currentSymbol}
        onSelectSymbol={handleSelectSymbol}
        onUpdateWatchlist={handleUpdateWatchlist}
      />

      <IndicatorsModal
        isOpen={isIndicatorsOpen}
        onClose={() => setIsIndicatorsOpen(false)}
        indicators={indicators}
        onToggleIndicator={handleToggleIndicator}
        onUpdateParams={handleUpdateIndicatorParams}
      />
    </div>
  );
}

export default App;
