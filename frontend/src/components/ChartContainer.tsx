import React, { useEffect, useRef, useState } from 'react';
import {
  createChart,
  createTextWatermark,
  CandlestickSeries,
  HistogramSeries,
  LineSeries,
  ColorType,
  CrosshairMode,
  PriceScaleMode,
} from 'lightweight-charts';
import type { IChartApi, ISeriesApi, LogicalRange, Time } from 'lightweight-charts';
import type { Candle, IndicatorConfig } from '../types';
import { captureHorizontalZoom, restoreHorizontalZoom } from '../utils/horizontalZoom';
import {
  computeSMA,
  computeEMA,
  computeBollingerBands,
  computeRSI,
  computeMACD,
} from '../utils/indicators';

const percentFormat = new Intl.NumberFormat('pt-BR', {
  style: 'percent', minimumFractionDigits: 2, maximumFractionDigits: 2, signDisplay: 'exceptZero',
});

interface ChartContainerProps {
  symbol: string;
  timeframe: string;
  candles: Candle[];
  isLogScale: boolean;
  indicators: IndicatorConfig[];
  isLoading: boolean;
  pricePrecision: number;
}

export const ChartContainer: React.FC<ChartContainerProps> = ({
  symbol,
  timeframe,
  candles,
  isLogScale,
  indicators,
  isLoading,
  pricePrecision,
}) => {
  const mainChartRef = useRef<HTMLDivElement>(null);

  const mainChartApi = useRef<IChartApi | null>(null);

  // Series refs
  const candleSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
  const volumeSeriesRef = useRef<ISeriesApi<'Histogram'> | null>(null);
  const smaSeriesRef = useRef<ISeriesApi<'Line'> | null>(null);
  const emaSeriesRef = useRef<ISeriesApi<'Line'> | null>(null);
  const bbUpperRef = useRef<ISeriesApi<'Line'> | null>(null);
  const bbMiddleRef = useRef<ISeriesApi<'Line'> | null>(null);
  const bbLowerRef = useRef<ISeriesApi<'Line'> | null>(null);

  const rsiSeriesRef = useRef<ISeriesApi<'Line'> | null>(null);
  const macdLineRef = useRef<ISeriesApi<'Line'> | null>(null);
  const macdSignalRef = useRef<ISeriesApi<'Line'> | null>(null);
  const macdHistRef = useRef<ISeriesApi<'Histogram'> | null>(null);

  // Zoom and pan preservation refs
  const userInteractedRef = useRef<boolean>(false);
  const interactionTimeoutRef = useRef<number | null>(null);
  const hasCustomZoomRef = useRef<boolean>(false);
  const savedZoomRef = useRef<{ span: number; offsetFromEnd: number } | null>(null);
  const isProgrammaticUpdateRef = useRef<boolean>(false);
  const updateSequenceRef = useRef(0);
  const candleCountRef = useRef<number>(0);
  const latestCandlesRef = useRef<Candle[]>(candles);
  const prevSymbolRef = useRef<string>(symbol);

  const [hoveredTime, setHoveredTime] = useState<number | null>(null);
  const hoveredIndex = hoveredTime === null ? -1 : candles.findIndex(c => c.time === hoveredTime);
  const legendIndex = hoveredIndex >= 0 ? hoveredIndex : candles.length - 1;
  const candle = candles[legendIndex];
  const previous = candles[legendIndex - 1];
  const change = candle && previous && previous.close !== 0
    ? (candle.close - previous.close) / previous.close
    : null;
  const candleColor = candle && candle.close >= candle.open ? 'up' : 'down';

  const rsi = indicators.find((i) => i.id === 'rsi');
  const macd = indicators.find((i) => i.id === 'macd');
  const rsiPeriod = Number(rsi?.params.period || 14);
  const macdWarmup = Math.max(Number(macd?.params.fast || 12), Number(macd?.params.slow || 26))
    + Number(macd?.params.signal || 9) - 1;
  const rsiLabel = rsi?.enabled ? `RSI (${rsiPeriod})` : null;
  const macdLabel = macd?.enabled
    ? `MACD (${macd.params.fast || 12}, ${macd.params.slow || 26}, ${macd.params.signal || 9})`
    : null;

  // Initialize or re-create main chart
  useEffect(() => {
    if (!mainChartRef.current) return;
    const chartElement = mainChartRef.current;

    const chart = createChart(chartElement, {
      autoSize: true,
      layout: {
        background: { type: ColorType.Solid, color: '#131722' },
        textColor: '#d1d4dc',
      },
      grid: {
        vertLines: { color: '#1e222d' },
        horzLines: { color: '#1e222d' },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
      },
      rightPriceScale: {
        borderColor: '#2b2b43',
        mode: PriceScaleMode.Normal,
        autoScale: true,
      },
      timeScale: {
        borderColor: '#2b2b43',
        timeVisible: true,
        secondsVisible: false,
      },
    });

    // Main Candlestick Series
    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: '#26a69a',
      downColor: '#ef5350',
      borderVisible: false,
      wickUpColor: '#26a69a',
      wickDownColor: '#ef5350',
    });

    // Volume Histogram (in bottom 20% of main price scale or separate)
    const volumeSeries = chart.addSeries(HistogramSeries, {
      priceFormat: { type: 'volume' },
      priceScaleId: 'volume_scale',
    });
    chart.priceScale('volume_scale').applyOptions({
      scaleMargins: {
        top: 0.8,
        bottom: 0,
      },
    });

    // Overlays
    const smaSeries = chart.addSeries(LineSeries, {
      color: '#f7931a',
      lineWidth: 2,
    });
    const emaSeries = chart.addSeries(LineSeries, {
      color: '#2962ff',
      lineWidth: 2,
    });
    const bbUpper = chart.addSeries(LineSeries, {
      color: '#ab47bc',
      lineWidth: 1,
    });
    const bbMiddle = chart.addSeries(LineSeries, {
      color: '#8e24aa',
      lineWidth: 1,
      lineStyle: 2,
    });
    const bbLower = chart.addSeries(LineSeries, {
      color: '#ab47bc',
      lineWidth: 1,
    });

    chart.panes()[0].setStretchFactor(3);
    mainChartApi.current = chart;
    candleSeriesRef.current = candleSeries;
    volumeSeriesRef.current = volumeSeries;
    smaSeriesRef.current = smaSeries;
    emaSeriesRef.current = emaSeries;
    bbUpperRef.current = bbUpper;
    bbMiddleRef.current = bbMiddle;
    bbLowerRef.current = bbLower;

    // Track user zoom and pan interactions
    const handleUserInteraction = (event: Event) => {
      if (event.type === 'pointermove' && !(event as PointerEvent).buttons) return;
      userInteractedRef.current = true;
      if (interactionTimeoutRef.current !== null) {
        window.clearTimeout(interactionTimeoutRef.current);
      }
      interactionTimeoutRef.current = window.setTimeout(() => {
        userInteractedRef.current = false;
      }, 1000);
    };

    const handleLogicalRangeChange = (newRange: LogicalRange | null) => {
      if (!newRange) return;
      if (isProgrammaticUpdateRef.current) return;

      if (userInteractedRef.current && latestCandlesRef.current.length > 0) {
        const zoom = captureHorizontalZoom(newRange, candleCountRef.current);
        if (zoom) {
          hasCustomZoomRef.current = true;
          savedZoomRef.current = zoom;
        }
      }
    };

    chart.timeScale().subscribeVisibleLogicalRangeChange(handleLogicalRangeChange);

    chartElement.addEventListener('wheel', handleUserInteraction, { passive: true, capture: true });
    chartElement.addEventListener('pointerdown', handleUserInteraction, { passive: true, capture: true });
    chartElement.addEventListener('pointermove', handleUserInteraction, { passive: true, capture: true });
    chartElement.addEventListener('touchstart', handleUserInteraction, { passive: true, capture: true });

    // Double-click to reset zoom back to full overview
    const handleDoubleClick = () => {
      hasCustomZoomRef.current = false;
      savedZoomRef.current = null;
      isProgrammaticUpdateRef.current = true;
      const updateId = ++updateSequenceRef.current;
      chart.timeScale().fitContent();
      chart.priceScale('right').applyOptions({ autoScale: true });
      requestAnimationFrame(() => {
        if (updateSequenceRef.current === updateId) isProgrammaticUpdateRef.current = false;
      });
    };
    chartElement.addEventListener('dblclick', handleDoubleClick);

    // Crosshair move listener for OHLC legend
    chart.subscribeCrosshairMove((param) => {
      setHoveredTime(param.point && typeof param.time === 'number' && param.seriesData.has(candleSeries)
        ? param.time
        : null);
    });

    return () => {
      if (interactionTimeoutRef.current !== null) {
        window.clearTimeout(interactionTimeoutRef.current);
      }
      chartElement.removeEventListener('wheel', handleUserInteraction, true);
      chartElement.removeEventListener('pointerdown', handleUserInteraction, true);
      chartElement.removeEventListener('pointermove', handleUserInteraction, true);
      chartElement.removeEventListener('touchstart', handleUserInteraction, true);
      chartElement.removeEventListener('dblclick', handleDoubleClick);
      chart.timeScale().unsubscribeVisibleLogicalRangeChange(handleLogicalRangeChange);
      chart.remove();
      mainChartApi.current = null;
    };
  }, []);

  // Update Scale Mode (Linear / Log)
  useEffect(() => {
    if (mainChartApi.current) {
      mainChartApi.current.priceScale('right').applyOptions({
        mode: isLogScale ? PriceScaleMode.Logarithmic : PriceScaleMode.Normal,
        autoScale: true,
      });
    }
  }, [isLogScale]);

  // Native panes share the candle time axis and keep independent value scales.
  useEffect(() => {
    const chart = mainChartApi.current;
    if (!chart || !rsiLabel) return;
    const pane = chart.addPane();
    const line = pane.addSeries(LineSeries, { color: '#e91e63', lineWidth: 2 });
    if (pane.paneIndex() !== 1) pane.moveTo(1);
    pane.setStretchFactor(1);
    const label = createTextWatermark(pane, {
      horzAlign: 'left', vertAlign: 'top',
      lines: [{ text: rsiLabel, color: '#aeb4c0', fontSize: 12 }],
    });
    rsiSeriesRef.current = line;
    return () => {
      rsiSeriesRef.current = null;
      if (mainChartApi.current !== chart) return;
      label.detach();
      chart.removeSeries(line);
    };
  }, [rsiLabel]);

  useEffect(() => {
    const chart = mainChartApi.current;
    if (!chart || !macdLabel) return;
    const pane = chart.addPane();
    const histogram = pane.addSeries(HistogramSeries);
    const line = pane.addSeries(LineSeries, { color: '#2962ff', lineWidth: 2 });
    const signal = pane.addSeries(LineSeries, { color: '#ff6d00', lineWidth: 1 });
    pane.setStretchFactor(1);
    const label = createTextWatermark(pane, {
      horzAlign: 'left', vertAlign: 'top',
      lines: [{ text: macdLabel, color: '#aeb4c0', fontSize: 12 }],
    });
    macdLineRef.current = line;
    macdSignalRef.current = signal;
    macdHistRef.current = histogram;
    return () => {
      macdLineRef.current = null;
      macdSignalRef.current = null;
      macdHistRef.current = null;
      if (mainChartApi.current !== chart) return;
      label.detach();
      chart.removeSeries(histogram);
      chart.removeSeries(line);
      chart.removeSeries(signal);
    };
  }, [macdLabel]);

  // Synchronize candles & indicator data
  useEffect(() => {
    if (!candleSeriesRef.current || !mainChartApi.current) return;
    // Guard before clearing or replacing any series: both change the time scale.
    isProgrammaticUpdateRef.current = true;
    const updateId = ++updateSequenceRef.current;
    requestAnimationFrame(() => requestAnimationFrame(() => {
      if (updateSequenceRef.current === updateId) isProgrammaticUpdateRef.current = false;
    }));
    if (candles.length === 0) {
      for (const series of [candleSeriesRef, volumeSeriesRef, smaSeriesRef, emaSeriesRef,
        bbUpperRef, bbMiddleRef, bbLowerRef, rsiSeriesRef, macdLineRef, macdSignalRef, macdHistRef]) {
        series.current?.setData([]);
      }
      latestCandlesRef.current = [];
      return;
    }
    const selectionChanged = prevSymbolRef.current !== `${symbol}_${timeframe}`;
    const priceFormat = { type: 'price' as const, precision: pricePrecision, minMove: 10 ** -pricePrecision };
    for (const series of [candleSeriesRef, smaSeriesRef, emaSeriesRef, bbUpperRef, bbMiddleRef, bbLowerRef,
      macdLineRef, macdSignalRef, macdHistRef]) {
      series.current?.applyOptions({ priceFormat });
    }

    latestCandlesRef.current = candles;
    prevSymbolRef.current = `${symbol}_${timeframe}`;

    // Only actual user interactions update savedZoomRef. Reading the range here
    // would capture the temporary/clamped viewport from a previous asset.

    // 1. Candlestick Data
    const formattedCandles = candles.map((c) => ({
      time: c.time as Time,
      open: c.open,
      high: c.high,
      low: c.low,
      close: c.close,
    }));
    candleSeriesRef.current.setData(formattedCandles);
    candleCountRef.current = candles.length;

    // 2. Volume Data
    if (volumeSeriesRef.current) {
      const volData = candles.map((c) => ({
        time: c.time as Time,
        value: c.volume,
        color: c.close >= c.open ? 'rgba(38, 166, 154, 0.4)' : 'rgba(239, 83, 80, 0.4)',
      }));
      volumeSeriesRef.current.setData(volData);
    }

    // 3. Overlays (SMA, EMA, Bollinger)
    const smaCfg = indicators.find((i) => i.id === 'sma');
    if (smaSeriesRef.current) {
      if (smaCfg?.enabled) {
        const smaData = computeSMA(candles, Number(smaCfg.params.period || 14));
        smaSeriesRef.current.setData(smaData);
      } else {
        smaSeriesRef.current.setData([]);
      }
    }

    const emaCfg = indicators.find((i) => i.id === 'ema');
    if (emaSeriesRef.current) {
      if (emaCfg?.enabled) {
        const emaData = computeEMA(candles, Number(emaCfg.params.period || 14));
        emaSeriesRef.current.setData(emaData);
      } else {
        emaSeriesRef.current.setData([]);
      }
    }

    const bbCfg = indicators.find((i) => i.id === 'bollinger');
    if (bbUpperRef.current && bbMiddleRef.current && bbLowerRef.current) {
      if (bbCfg?.enabled) {
        const bbData = computeBollingerBands(
          candles,
          Number(bbCfg.params.period || 20),
          Number(bbCfg.params.stdDev || 2)
        );
        bbUpperRef.current.setData(bbData.upper);
        bbMiddleRef.current.setData(bbData.middle);
        bbLowerRef.current.setData(bbData.lower);
      } else {
        bbUpperRef.current.setData([]);
        bbMiddleRef.current.setData([]);
        bbLowerRef.current.setData([]);
      }
    }

    // 4. Panel Indicators (RSI)
    const rsiCfg = indicators.find((i) => i.id === 'rsi');
    if (rsiSeriesRef.current && rsiCfg?.enabled) {
      const rsiData = computeRSI(candles, Number(rsiCfg.params.period || 14));
      rsiSeriesRef.current.setData(rsiData);
    }

    // 5. Panel Indicators (MACD)
    const macdCfg = indicators.find((i) => i.id === 'macd');
    if (macdLineRef.current && macdSignalRef.current && macdHistRef.current && macdCfg?.enabled) {
      const macdData = computeMACD(
        candles,
        Number(macdCfg.params.fast || 12),
        Number(macdCfg.params.slow || 26),
        Number(macdCfg.params.signal || 9)
      );
      macdLineRef.current.setData(macdData.macd);
      macdSignalRef.current.setData(macdData.signal);
      macdHistRef.current.setData(macdData.hist);
    }

    // Keep the user's horizontal span even if this asset has fewer candles.
    const targetRange = hasCustomZoomRef.current && savedZoomRef.current
      ? restoreHorizontalZoom(savedZoomRef.current, candles.length)
      : null;
    if (targetRange) {
      mainChartApi.current.timeScale().setVisibleLogicalRange(targetRange as LogicalRange);
    } else {
      mainChartApi.current.timeScale().fitContent();
    }

    // Ensure price scale automatically recalculates vertical bounds for new asset
    if (selectionChanged) mainChartApi.current.priceScale('right').applyOptions({
      autoScale: true,
    });

    requestAnimationFrame(() => {
      if (selectionChanged) mainChartApi.current?.priceScale('right').applyOptions({
        autoScale: true,
      });
    });
  }, [candles, indicators, symbol, timeframe, pricePrecision]);

  return (
    <div className="chart-view-wrapper">
      {/* Chart Legend / Floating OHLC Tooltip */}
      <div className="chart-header-legend">
        <div className="legend-symbol-block">
          <span className="legend-symbol">{symbol}</span>
          <span className="legend-timeframe">{timeframe}</span>
          {candle && (
            <span className="legend-change">
              Variação <strong className={change !== null && change > 0 ? 'up' : change !== null && change < 0 ? 'down' : undefined}>
                {change === null ? '—' : percentFormat.format(change)}
              </strong>
            </span>
          )}
        </div>

        {candle && (
          <div className="legend-values">
            <span>A: <strong className={candleColor}>{candle.open.toFixed(pricePrecision)}</strong></span>
            <span>M: <strong className={candleColor}>{candle.high.toFixed(pricePrecision)}</strong></span>
            <span>m: <strong className={candleColor}>{candle.low.toFixed(pricePrecision)}</strong></span>
            <span>F: <strong className={candleColor}>{candle.close.toFixed(pricePrecision)}</strong></span>
            <span>Vol: <strong>{candle.volume.toFixed(3)}</strong></span>
            <span className="legend-time">{new Date(candle.time * 1000).toISOString().replace('T', ' ').slice(0, 16)} UTC</span>
          </div>
        )}

        {candles.length > 0 && candles[candles.length - 1].is_complete === false && (
          <span className="loading-tag">Último candle em formação</span>
        )}
        {rsi?.enabled && candles.length > 0 && candles.length <= rsiPeriod && (
          <span className="loading-tag">RSI requer {rsiPeriod + 1} candles</span>
        )}
        {macd?.enabled && candles.length > 0 && candles.length < macdWarmup && (
          <span className="loading-tag">Sinal do MACD requer {macdWarmup} candles</span>
        )}
        {isLoading && <span className="loading-tag">Carregando dados...</span>}
      </div>

      <div ref={mainChartRef} className="main-chart-canvas" />
    </div>
  );
};
