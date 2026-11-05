import React from 'react';
import { X, Check } from 'lucide-react';
import type { IndicatorConfig } from '../types';

interface IndicatorsModalProps {
  isOpen: boolean;
  onClose: () => void;
  indicators: IndicatorConfig[];
  onToggleIndicator: (id: string) => void;
  onUpdateParams: (id: string, params: Record<string, number | string>) => void;
}

export const IndicatorsModal: React.FC<IndicatorsModalProps> = ({
  isOpen,
  onClose,
  indicators,
  onToggleIndicator,
  onUpdateParams,
}) => {
  if (!isOpen) return null;

  return (
    <div className="drawer-overlay" onClick={onClose}>
      <div className="modal-panel" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>Indicadores Técnicos</h3>
          <button className="icon-btn" onClick={onClose}>
            <X size={18} />
          </button>
        </div>

        <div className="modal-content">
          <p className="modal-desc">
            Ative e ajuste os indicadores técnicos. Todas as configurações permanecem ativas durante a rotação automática entre ativos.
          </p>

          <div className="indicators-grid">
            {indicators.map((ind) => (
              <div
                key={ind.id}
                className={`indicator-card ${ind.enabled ? 'enabled' : ''}`}
              >
                <div className="card-top">
                  <div className="card-title-group">
                    <span
                      className="indicator-color-dot"
                      style={{ backgroundColor: ind.color }}
                    />
                    <span className="indicator-title">{ind.name}</span>
                    <span className="indicator-type-tag">
                      {ind.type === 'overlay' ? 'Sobreposto' : 'Painel'}
                    </span>
                  </div>

                  <button
                    className={`toggle-switch-btn ${ind.enabled ? 'on' : 'off'}`}
                    onClick={() => onToggleIndicator(ind.id)}
                  >
                    {ind.enabled ? <Check size={14} /> : null}
                  </button>
                </div>

                {ind.enabled && (
                  <div className="params-row">
                    {Object.entries(ind.params).map(([key, val]) => (
                      <div key={key} className="param-field">
                        <label>{key.toUpperCase()}:</label>
                        <input
                          type="number"
                          value={val}
                          onChange={(e) =>
                            onUpdateParams(ind.id, {
                              ...ind.params,
                              [key]: parseFloat(e.target.value) || 0,
                            })
                          }
                        />
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
