import React, { useState } from 'react';
import { X, ChevronUp, ChevronDown, Trash2, Plus } from 'lucide-react';

interface WatchlistDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  watchlist: string[];
  currentSymbol: string;
  onSelectSymbol: (symbol: string) => void;
  onUpdateWatchlist: (newList: string[]) => void;
}

export const WatchlistDrawer: React.FC<WatchlistDrawerProps> = ({
  isOpen,
  onClose,
  watchlist,
  currentSymbol,
  onSelectSymbol,
  onUpdateWatchlist,
}) => {
  const [newSymbolInput, setNewSymbolInput] = useState('');

  if (!isOpen) return null;

  const handleAdd = () => {
    const s = newSymbolInput.trim().toUpperCase();
    if (s && !watchlist.includes(s)) {
      onUpdateWatchlist([...watchlist, s]);
      setNewSymbolInput('');
    }
  };

  const handleRemove = (symbol: string) => {
    if (watchlist.length <= 1) return; // Keep at least one symbol
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

  return (
    <div className="drawer-overlay" onClick={onClose}>
      <div className="drawer-panel" onClick={(e) => e.stopPropagation()}>
        <div className="drawer-header">
          <h3>Lista de Ativos para Rotação</h3>
          <button className="icon-btn" onClick={onClose}>
            <X size={18} />
          </button>
        </div>

        <div className="drawer-content">
          <p className="drawer-desc">
            Organize a sequência que será percorrida automaticamente ao pressionar <strong>Play</strong>.
          </p>

          <div className="add-symbol-bar">
            <input
              type="text"
              placeholder="Adicionar símbolo (ex: AVAXUSDT)..."
              value={newSymbolInput}
              onChange={(e) => setNewSymbolInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleAdd()}
            />
            <button className="btn-add" onClick={handleAdd}>
              <Plus size={16} /> Adicionar
            </button>
          </div>

          <div className="watchlist-items-list">
            {watchlist.map((symbol, idx) => (
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
