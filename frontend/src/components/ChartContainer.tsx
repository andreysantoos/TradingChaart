import React, { useEffect, useRef, useState } from 'react';
import {
  createChart,
  CandlestickSeries,
  HistogramSeries,
  LineSeries,
  ColorType,
  CrosshairMode,
  PriceScaleMode,
} from 'lightweight-charts';
import type { IChartApi, ISeriesApi, Time } from 'lightweight-charts';
import type { Candle, IndicatorConfig } from '../types';
import {
  computeSMA,
  computeEMA,
  computeBollingerBands,
  computeRSI,
  computeMACD,
} from '../utils/indicators';

interface ChartContainerProps {
  symbol: string;
  timeframe: string;
  candles: Candle[];
  isLogScale: boolean;
  indicators: IndicatorConfig[];
  isLoading: boolean;
}

export const ChartContainer: React.FC<ChartContainerProps> = ({
  symbol,
  timeframe,
  candles,
  isLogScale,
  indicators,
  isLoading,
}) => {
  const mainChartRef = useRef<HTMLDivElement>(null);
  const rsiChartRef = useRef<HTMLDivElement>(null);
  const macdChartRef = useRef<HTMLDivElement>(null);

  const mainChartApi = useRef<IChartApi | null>(null);
  const rsiChartApi = useRef<IChartApi | null>(null);
  const macdChartApi = useRef<IChartApi | null>(null);

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

  // Hover legend state
  const [legendInfo, setLegendInfo] = useState<{
    time?: string;
    open?: number;
    high?: number;
    low?: number;
    close?: number;
    volume?: number;
  }>({});

  const isRsiEnabled = indicators.find((i) => i.id === 'rsi')?.enabled;
  const isMacdEnabled = indicators.find((i) => i.id === 'macd')?.enabled;

  // Initialize or re-create main chart
  useEffect(() => {
    if (!mainChartRef.current) return;

    const chart = createChart(mainChartRef.current, {
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
        mode: isLogScale ? PriceScaleMode.Logarithmic : PriceScaleMode.Normal,
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

    mainChartApi.current = chart;
    candleSeriesRef.current = candleSeries;
    volumeSeriesRef.current = volumeSeries;
    smaSeriesRef.current = smaSeries;
    emaSeriesRef.current = emaSeries;
    bbUpperRef.current = bbUpper;
    bbMiddleRef.current = bbMiddle;
    bbLowerRef.current = bbLower;

    // Crosshair move listener for OHLC legend
    chart.subscribeCrosshairMove((param) => {
      if (
        param.point === undefined ||
        !param.time ||
        param.point.x < 0 ||
        param.point.y < 0
      ) {
        if (candles.length > 0) {
          const last = candles[candles.length - 1];
          setLegendInfo({
            time: new Date(last.time * 1000).toISOString().replace('T', ' ').slice(0, 16) + ' UTC',
            open: last.open,
            high: last.high,
            low: last.low,
            close: last.close,
            volume: last.volume,
          });
        }
      } else {
        const cData = param.seriesData.get(candleSeries) as any;
        const vData = param.seriesData.get(volumeSeries) as any;
        if (cData) {
          setLegendInfo({
            time: typeof param.time === 'number'
              ? new Date(param.time * 1000).toISOString().replace('T', ' ').slice(0, 16) + ' UTC'
              : String(param.time),
            open: cData.open,
            high: cData.high,
            low: cData.low,
            close: cData.close,
            volume: vData?.value,
          });
        }
      }
    });

    // Resize observer
    const handleResize = () => {
      if (mainChartRef.current && chart) {
        chart.applyOptions({
          width: mainChartRef.current.clientWidth,
          height: mainChartRef.current.clientHeight,
        });
      }
    };
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
      mainChartApi.current = null;
    };
  }, []);

  // Update Scale Mode (Linear / Log)
  useEffect(() => {
    if (mainChartApi.current) {
      mainChartApi.current.priceScale('right').applyOptions({
        mode: isLogScale ? PriceScaleMode.Logarithmic : PriceScaleMode.Normal,
      });
    }
  }, [isLogScale]);

  // RSI Chart Lifecycle
  useEffect(() => {
    if (!isRsiEnabled || !rsiChartRef.current) {
      if (rsiChartApi.current) {
        rsiChartApi.current.remove();
        rsiChartApi.current = null;
      }
      return;
    }

    const rChart = createChart(rsiChartRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: '#131722' },
        textColor: '#d1d4dc',
      },
      grid: { vertLines: { color: '#1e222d' }, horzLines: { color: '#1e222d' } },
      rightPriceScale: { borderColor: '#2b2b43' },
      timeScale: { visible: false },
    });

    const rSeries = rChart.addSeries(LineSeries, {
      color: '#e91e63',
      lineWidth: 2,
    });
    rsiChartApi.current = rChart;
    rsiSeriesRef.current = rSeries;

    return () => {
      rChart.remove();
      rsiChartApi.current = null;
    };
  }, [isRsiEnabled]);

  // MACD Chart Lifecycle
  useEffect(() => {
    if (!isMacdEnabled || !macdChartRef.current) {
      if (macdChartApi.current) {
        macdChartApi.current.remove();
        macdChartApi.current = null;
      }
      return;
    }

    const mChart = createChart(macdChartRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: '#131722' },
        textColor: '#d1d4dc',
      },
      grid: { vertLines: { color: '#1e222d' }, horzLines: { color: '#1e222d' } },
      rightPriceScale: { borderColor: '#2b2b43' },
      timeScale: { visible: false },
    });

    const mLine = mChart.addSeries(LineSeries, { color: '#2962ff', lineWidth: 2 });
    const mSignal = mChart.addSeries(LineSeries, { color: '#ff6d00', lineWidth: 1 });
    const mHist = mChart.addSeries(HistogramSeries, {});

    macdChartApi.current = mChart;
    macdLineRef.current = mLine;
    macdSignalRef.current = mSignal;
    macdHistRef.current = mHist;

    return () => {
      mChart.remove();
      macdChartApi.current = null;
    };
  }, [isMacdEnabled]);

  // Synchronize candles & indicator data
  useEffect(() => {
    if (!candles || candles.length === 0 || !candleSeriesRef.current) return;

    // 1. Candlestick Data
    const formattedCandles = candles.map((c) => ({
      time: c.time as Time,
      open: c.open,
      high: c.high,
      low: c.low,
      close: c.close,
    }));
    candleSeriesRef.current.setData(formattedCandles);

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

    // Fit content smoothly on symbol change
    mainChartApi.current?.timeScale().fitContent();

    // Default hover info to latest candle
    const last = candles[candles.length - 1];
    setLegendInfo({
      time: new Date(last.time * 1000).toISOString().replace('T', ' ').slice(0, 16) + ' UTC',
      open: last.open,
      high: last.high,
      low: last.low,
      close: last.close,
      volume: last.volume,
    });
  }, [candles, indicators]);

  return (
    <div className="chart-view-wrapper">
      {/* Chart Legend / Floating OHLC Tooltip */}
      <div className="chart-header-legend">
        <div className="legend-symbol-block">
          <span className="legend-symbol">{symbol}</span>
          <span className="legend-timeframe">{timeframe}</span>
        </div>

        {legendInfo.open !== undefined && (
          <div className="legend-values">
            <span>A: <strong className={legendInfo.close! >= legendInfo.open! ? 'up' : 'down'}>{legendInfo.open.toFixed(2)}</strong></span>
            <span>M: <strong className={legendInfo.close! >= legendInfo.open! ? 'up' : 'down'}>{legendInfo.high?.toFixed(2)}</strong></span>
            <span>m: <strong className={legendInfo.close! >= legendInfo.open! ? 'up' : 'down'}>{legendInfo.low?.toFixed(2)}</strong></span>
            <span>F: <strong className={legendInfo.close! >= legendInfo.open! ? 'up' : 'down'}>{legendInfo.close?.toFixed(2)}</strong></span>
            <span>Vol: <strong>{legendInfo.volume?.toFixed(3)}</strong></span>
            {legendInfo.time && <span className="legend-time">{legendInfo.time}</span>}
          </div>
        )}

        {isLoading && <span className="loading-tag">Carregando dados...</span>}
      </div>

      {/* Main Chart Canvas */}
      <div
        ref={mainChartRef}
        className="main-chart-canvas"
        style={{
          flex: isRsiEnabled || isMacdEnabled ? '1 1 65%' : '1 1 100%',
        }}
      />

      {/* Secondary RSI Panel */}
      {isRsiEnabled && (
        <div className="sub-panel">
          <div className="sub-panel-title">RSI (14)</div>
          <div ref={rsiChartRef} className="sub-chart-canvas" />
        </div>
      )}

      {/* Secondary MACD Panel */}
      {isMacdEnabled && (
        <div className="sub-panel">
          <div className="sub-panel-title">MACD (12, 26, 9)</div>
          <div ref={macdChartRef} className="sub-chart-canvas" />
        </div>
      )}
    </div>
  );
};
