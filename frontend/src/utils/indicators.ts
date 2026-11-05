import type { Candle } from '../types';
import type { Time } from 'lightweight-charts';

export interface LinePoint {
  time: Time;
  value: number;
}

export interface HistogramPoint {
  time: Time;
  value: number;
  color?: string;
}

export function computeSMA(candles: Candle[], period = 14): LinePoint[] {
  const points: LinePoint[] = [];
  if (candles.length < period) return points;

  let sum = 0;
  for (let i = 0; i < period; i++) {
    sum += candles[i].close;
  }
  points.push({ time: candles[period - 1].time as Time, value: sum / period });

  for (let i = period; i < candles.length; i++) {
    sum += candles[i].close - candles[i - period].close;
    points.push({ time: candles[i].time as Time, value: sum / period });
  }
  return points;
}

export function computeEMA(candles: Candle[], period = 14): LinePoint[] {
  const points: LinePoint[] = [];
  if (candles.length < period) return points;

  const multiplier = 2 / (period + 1);
  let sum = 0;
  for (let i = 0; i < period; i++) {
    sum += candles[i].close;
  }
  let prevEMA = sum / period;
  points.push({ time: candles[period - 1].time as Time, value: prevEMA });

  for (let i = period; i < candles.length; i++) {
    const currentEMA = (candles[i].close - prevEMA) * multiplier + prevEMA;
    points.push({ time: candles[i].time as Time, value: currentEMA });
    prevEMA = currentEMA;
  }
  return points;
}

export function computeBollingerBands(
  candles: Candle[],
  period = 20,
  stdDevMult = 2
): { upper: LinePoint[]; middle: LinePoint[]; lower: LinePoint[] } {
  const upper: LinePoint[] = [];
  const middle: LinePoint[] = [];
  const lower: LinePoint[] = [];

  if (candles.length < period) return { upper, middle, lower };

  for (let i = period - 1; i < candles.length; i++) {
    const slice = candles.slice(i - period + 1, i + 1);
    const mean = slice.reduce((acc, c) => acc + c.close, 0) / period;
    const variance = slice.reduce((acc, c) => acc + Math.pow(c.close - mean, 2), 0) / period;
    const stdDev = Math.sqrt(variance);

    const t = candles[i].time as Time;
    middle.push({ time: t, value: mean });
    upper.push({ time: t, value: mean + stdDevMult * stdDev });
    lower.push({ time: t, value: mean - stdDevMult * stdDev });
  }

  return { upper, middle, lower };
}

export function computeRSI(candles: Candle[], period = 14): LinePoint[] {
  const points: LinePoint[] = [];
  if (candles.length <= period) return points;

  const gains: number[] = [];
  const losses: number[] = [];
  for (let i = 1; i < candles.length; i++) {
    const diff = candles[i].close - candles[i - 1].close;
    gains.push(diff > 0 ? diff : 0);
    losses.push(diff < 0 ? -diff : 0);
  }

  let avgGain = gains.slice(0, period).reduce((a, b) => a + b, 0) / period;
  let avgLoss = losses.slice(0, period).reduce((a, b) => a + b, 0) / period;

  let rsi = avgLoss === 0 ? 100 : 100 - 100 / (1 + avgGain / avgLoss);
  points.push({ time: candles[period].time as Time, value: rsi });

  for (let i = period; i < gains.length; i++) {
    avgGain = (avgGain * (period - 1) + gains[i]) / period;
    avgLoss = (avgLoss * (period - 1) + losses[i]) / period;
    rsi = avgLoss === 0 ? 100 : 100 - 100 / (1 + avgGain / avgLoss);
    points.push({ time: candles[i + 1].time as Time, value: rsi });
  }

  return points;
}

export function computeMACD(
  candles: Candle[],
  fastPeriod = 12,
  slowPeriod = 26,
  signalPeriod = 9
): { macd: LinePoint[]; signal: LinePoint[]; hist: HistogramPoint[] } {
  const macdPoints: LinePoint[] = [];
  const signalPoints: LinePoint[] = [];
  const histPoints: HistogramPoint[] = [];

  const fastEMA = computeEMA(candles, fastPeriod);
  const slowEMA = computeEMA(candles, slowPeriod);

  const fastMap = new Map<number, number>(fastEMA.map((p) => [p.time as number, p.value]));
  const macdRaw: { time: number; value: number }[] = [];

  for (const s of slowEMA) {
    const fVal = fastMap.get(s.time as number);
    if (fVal !== undefined) {
      const macdVal = fVal - s.value;
      macdPoints.push({ time: s.time, value: macdVal });
      macdRaw.push({ time: s.time as number, value: macdVal });
    }
  }

  if (macdRaw.length >= signalPeriod) {
    const multiplier = 2 / (signalPeriod + 1);
    let sum = 0;
    for (let i = 0; i < signalPeriod; i++) {
      sum += macdRaw[i].value;
    }
    let prevSignal = sum / signalPeriod;
    signalPoints.push({ time: macdRaw[signalPeriod - 1].time as Time, value: prevSignal });
    
    const hInit = macdRaw[signalPeriod - 1].value - prevSignal;
    histPoints.push({
      time: macdRaw[signalPeriod - 1].time as Time,
      value: hInit,
      color: hInit >= 0 ? '#26a69a' : '#ef5350',
    });

    for (let i = signalPeriod; i < macdRaw.length; i++) {
      const curSignal = (macdRaw[i].value - prevSignal) * multiplier + prevSignal;
      const t = macdRaw[i].time as Time;
      signalPoints.push({ time: t, value: curSignal });
      const h = macdRaw[i].value - curSignal;
      histPoints.push({
        time: t,
        value: h,
        color: h >= 0 ? '#26a69a' : '#ef5350',
      });
      prevSignal = curSignal;
    }
  }

  return { macd: macdPoints, signal: signalPoints, hist: histPoints };
}
