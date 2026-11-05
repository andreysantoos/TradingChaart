import React, { useState, useMemo } from 'react';
import { X, ChevronUp, ChevronDown, Trash2, Plus, Search, RotateCcw } from 'lucide-react';

interface WatchlistDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  watchlist: string[];
  currentSymbol: string;
  onSelectSymbol: (symbol: string) => void;
  onUpdateWatchlist: (newList: string[]) => void;
}

const TOP_20_SYMBOLS = [
  'BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT',
  'DOGEUSDT', 'ADAUSDT', 'AVAXUSDT', 'SUIUSDT', 'LINKUSDT',
  'NEARUSDT', 'DOTUSDT', 'LTCUSDT', 'APTUSDT', 'TRXUSDT',
  'BCHUSDT', 'PEPEUSDT', 'SHIBUSDT', 'UNIUSDT', 'TAOUSDT'
];

const TOP_5_SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT'];

export const WatchlistDrawer: React.FC<WatchlistDrawerProps> = ({
  isOpen,
  onClose,
  watchlist,
  currentSymbol,
  onSelectSymbol,
  onUpdateWatchlist,
}) => {
  const [newSymbolInput, setNewSymbolInput] = useState('');
  const [filterQuery, setFilterQuery] = useState('');

  const filteredItems = useMemo(() => {
    if (!filterQuery) return watchlist.map((sym, idx) => ({ sym, idx }));
    const q = filterQuery.toUpperCase();
    return watchlist
      .map((sym, idx) => ({ sym, idx }))
      .filter((item) => item.sym.includes(q));
  }, [watchlist, filterQuery]);

  if (!isOpen) return null;

  const handleAdd = () => {
    const s = newSymbolInput.trim().toUpperCase();
    if (s && !watchlist.includes(s)) {
      onUpdateWatchlist([...watchlist, s]);
      setNewSymbolInput('');
    }
  };

  const handleRemove = (symbol: string) => {
    if (watchlist.length <= 1) return;
    onUpdateWatchlist(watchlist.filter((s) => s !== symbol));
  };

  const moveUp = (index: number) => {
    if (index === 0) return;
    const copy = [...watchlist];
    const temp = copy[index - 1];
    copy[index - 1] = copy[index];
    copy[index] = temp;
    onUpdateWatchlist(copy);
  };

  const moveDown = (index: number) => {
    if (index === watchlist.length - 1) return;
    const copy = [...watchlist];
    const temp = copy[index + 1];
    copy[index + 1] = copy[index];
    copy[index] = temp;
    onUpdateWatchlist(copy);
  };

  const handleLoadAll = async () => {
    try {
      const res = await fetch('/api/markets/symbols');
      if (res.ok) {
        const data = await res.json();
        const all = data.map((s: { symbol: string }) => s.symbol);
        onUpdateWatchlist(all);
      }
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div className="drawer-overlay" onClick={onClose}>
      <div className="drawer-panel" onClick={(e) => e.stopPropagation()}>
        <div className="drawer-header">
          <h3>Lista de Rotação ({watchlist.length})</h3>
          <button className="icon-btn" onClick={onClose}>
            <X size={18} />
          </button>
        </div>

        <div className="drawer-content">
          <p className="drawer-desc">
            Organize a sequência que será percorrida automaticamente ao pressionar <strong>Play</strong>.
          </p>

          {/* Preset Buttons */}
          <div className="preset-buttons-row">
            <button className="preset-btn" onClick={handleLoadAll} title="Carregar todos os 522 contratos ativos">
              Todos (522)
            </button>
            <button className="preset-btn" onClick={() => onUpdateWatchlist(TOP_20_SYMBOLS)} title="Carregar Top 20">
              Top 20
            </button>
            <button className="preset-btn" onClick={() => onUpdateWatchlist(TOP_5_SYMBOLS)} title="Carregar Top 5">
              <RotateCcw size={12} /> Top 5
            </button>
          </div>

          {/* Add custom symbol */}
          <div className="add-symbol-bar">
            <input
              type="text"
              placeholder="Adicionar contrato (ex: SUIUSDT)..."
              value={newSymbolInput}
              onChange={(e) => setNewSymbolInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleAdd()}
            />
            <button className="btn-add" onClick={handleAdd}>
              <Plus size={16} /> Adicionar
            </button>
          </div>

          {/* Filter existing in list */}
          {watchlist.length > 15 && (
            <div className="filter-watchlist-bar">
              <Search size={14} className="filter-icon" />
              <input
                type="text"
                placeholder="Filtrar na lista..."
                value={filterQuery}
                onChange={(e) => setFilterQuery(e.target.value)}
              />
            </div>
          )}

          {/* List items */}
          <div className="watchlist-items-list">
            {filteredItems.map(({ sym: symbol, idx }) => (
              <div
                key={symbol}
                className={`watchlist-item-row ${symbol === currentSymbol ? 'current' : ''}`}
              >
                <div className="item-left" onClick={() => onSelectSymbol(symbol)}>
                  <span className="item-order">{idx + 1}</span>
                  <span className="item-name">{symbol}</span>
                  {symbol === currentSymbol && <span className="active-pill">EXIBINDO</span>}
                </div>

                <div className="item-actions">
                  <button
                    disabled={idx === 0}
                    onClick={() => moveUp(idx)}
                    title="Mover para cima"
                  >
                    <ChevronUp size={16} />
                  </button>
                  <button
                    disabled={idx === watchlist.length - 1}
                    onClick={() => moveDown(idx)}
                    title="Mover para baixo"
                  >
                    <ChevronDown size={16} />
                  </button>
                  <button
                    className="btn-delete"
                    disabled={watchlist.length <= 1}
                    onClick={() => handleRemove(symbol)}
                    title="Remover da lista"
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
