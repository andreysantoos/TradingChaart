import React, { useState } from 'react';
import { Play, Pause, Square, SlidersHorizontal, List, Search } from 'lucide-react';
import type { HealthData, SymbolInfo, Timeframe } from '../types';

interface HeaderProps {
  currentSymbol: string;
  onSelectSymbol: (symbol: string) => void;
  symbols: SymbolInfo[];
  timeframe: Timeframe;
  onSelectTimeframe: (tf: Timeframe) => void;
  isLogScale: boolean;
  onToggleScale: () => void;
  isPlaying: boolean;
  onTogglePlay: () => void;
  onStopPlay: () => void;
  rotationInterval: number;
  onChangeInterval: (sec: number) => void;
  watchlistLength: number;
  activeWatchlistIndex: number;
  timerProgress: number; // 0 to 100
  onOpenIndicators: () => void;
  onOpenWatchlist: () => void;
  health: HealthData | null;
}

const TIMEFRAMES: Timeframe[] = ['1m', '5m', '15m', '30m', '1h', '4h', '1d', '1w'];

export const Header: React.FC<HeaderProps> = ({
  currentSymbol,
  onSelectSymbol,
  symbols,
  timeframe,
  onSelectTimeframe,
  isLogScale,
  onToggleScale,
  isPlaying,
  onTogglePlay,
  onStopPlay,
  rotationInterval,
  onChangeInterval,
  watchlistLength,
  activeWatchlistIndex,
  timerProgress,
  onOpenIndicators,
  onOpenWatchlist,
  health,
}) => {
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  const filteredSymbols = symbols.filter(
    (s) =>
      s.symbol.toLowerCase().includes(searchQuery.toLowerCase()) ||
      s.base_asset.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <header className="header-container">
      {/* Top Bar */}
      <div className="header-main">
        {/* Brand & Symbol Selector */}
        <div className="header-section">
          <div className="brand-logo">
            <span className="brand-title">REA</span>
            <span className="brand-badge">TERMINAL</span>
          </div>

          <div className="symbol-dropdown-container">
            <button
              className="symbol-selector-btn"
              onClick={() => setIsSearchOpen(!isSearchOpen)}
            >
              <span className="symbol-name">{currentSymbol}</span>
              <span className="market-tag">USDS-M FUTURES</span>
              <Search size={14} className="icon-search" />
            </button>

            {isSearchOpen && (
              <div className="symbol-modal">
                <input
                  type="text"
                  placeholder="Pesquisar contrato (ex: BTC, ETH)..."
                  className="symbol-search-input"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  autoFocus
                />
                <div className="symbol-list">
                  {filteredSymbols.slice(0, 50).map((s) => (
                    <div
                      key={s.symbol}
                      className={`symbol-item ${s.symbol === currentSymbol ? 'active' : ''}`}
                      onClick={() => {
                        onSelectSymbol(s.symbol);
                        setIsSearchOpen(false);
                      }}
                    >
                      <span className="item-symbol">{s.symbol}</span>
                      <span className="item-base">{s.base_asset} / {s.quote_asset}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Timeframe Selectors */}
        <div className="timeframe-group">
          {TIMEFRAMES.map((tf) => (
            <button
              key={tf}
              className={`tf-btn ${timeframe === tf ? 'active' : ''}`}
              onClick={() => onSelectTimeframe(tf)}
            >
              {tf}
            </button>
          ))}
        </div>

        {/* Scale & Indicator Tools */}
        <div className="header-section">
          <button
            className={`tool-btn ${isLogScale ? 'active' : ''}`}
            onClick={onToggleScale}
            title="Alternar entre Escala Linear e Logarítmica"
          >
            {isLogScale ? 'LOG' : 'LIN'}
          </button>

          <button
            className="tool-btn icon-label-btn"
            onClick={onOpenIndicators}
            title="Configurar Indicadores Técnicos"
          >
            <SlidersHorizontal size={15} />
            <span>Indicadores</span>
          </button>
        </div>

        {/* Play & Auto-Rotation Controller */}
        <div className="rotation-control-panel">
          <button
            className={`play-btn ${isPlaying ? 'playing' : ''}`}
            onClick={onTogglePlay}
            title={isPlaying ? 'Pausar Rotação' : 'Iniciar Rotação Automática'}
          >
            {isPlaying ? <Pause size={16} /> : <Play size={16} />}
            <span>{isPlaying ? 'PAUSE' : 'PLAY'}</span>
          </button>

          {isPlaying && (
            <button
              className="stop-btn"
              onClick={onStopPlay}
              title="Interromper Rotação"
            >
              <Square size={14} />
            </button>
          )}

          <div className="interval-control">
            <label>Intervalo:</label>
            <input
              type="number"
              min={5}
              max={120}
              value={rotationInterval}
              onChange={(e) => onChangeInterval(Math.max(5, parseInt(e.target.value) || 5))}
              className="interval-input"
            />
            <span className="unit">s</span>
          </div>

          <div className="rotation-info-badge">
            <span className="badge-count">
              {watchlistLength > 0 ? `${activeWatchlistIndex + 1}/${watchlistLength}` : '0/0'}
            </span>
          </div>

          <button
            className="tool-btn icon-label-btn watchlist-btn"
            onClick={onOpenWatchlist}
            title="Gerenciar Lista de Rotação"
          >
            <List size={16} />
            <span>Lista ({watchlistLength})</span>
          </button>
        </div>

        {/* Health / System Status */}
        <div className="health-badge-container">
          <div
            className={`health-dot ${health?.status === 'healthy' ? 'healthy' : 'pending'}`}
          />
          <div className="health-text">
            <span className="health-title">Pipeline 1m</span>
            <span className="health-detail">
              {health ? `${health.total_1m_candles_stored} velas` : 'Conectando...'}
            </span>
          </div>
        </div>
      </div>

      {/* Rotation Progress Bar */}
      {isPlaying && (
        <div className="rotation-progress-bar-container">
          <div
            className="rotation-progress-bar"
            style={{ width: `${timerProgress}%` }}
          />
        </div>
      )}
    </header>
  );
};
