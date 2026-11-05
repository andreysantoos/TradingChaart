import test from 'node:test';
import assert from 'node:assert/strict';
import { captureHorizontalZoom, restoreHorizontalZoom } from '../src/utils/horizontalZoom.ts';

test('weekly zoom survives a shorter asset and return to original asset', () => {
  const zoom = captureHorizontalZoom({ from: 15, to: 115 }, 120);
  assert.deepEqual(restoreHorizontalZoom(zoom, 40), { from: -65, to: 35 });
  assert.deepEqual(restoreHorizontalZoom(zoom, 120), { from: 15, to: 115 });
});

test('empty loading state does not supply a replacement viewport', () => {
  const zoom = captureHorizontalZoom({ from: 50, to: 90 }, 96);
  assert.equal(captureHorizontalZoom({ from: 0, to: 10 }, 0), null);
  assert.equal(restoreHorizontalZoom(zoom, 0), null);
  assert.deepEqual(restoreHorizontalZoom(zoom, 96), { from: 50, to: 90 });
});

test('pan outside shorter history falls back to tail without changing zoom preference', () => {
  const zoom = captureHorizontalZoom({ from: 10, to: 30 }, 120);
  assert.deepEqual(restoreHorizontalZoom(zoom, 10), { from: -11, to: 9 });
  assert.deepEqual(restoreHorizontalZoom(zoom, 120), { from: 10, to: 30 });
});

test('right margin and horizontal span survive updates and a new candle', () => {
  const zoom = captureHorizontalZoom({ from: 60, to: 105 }, 96);
  assert.deepEqual(restoreHorizontalZoom(zoom, 96), { from: 60, to: 105 });
  assert.deepEqual(restoreHorizontalZoom(zoom, 97), { from: 61, to: 106 });
});
