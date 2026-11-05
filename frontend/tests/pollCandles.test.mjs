import test from 'node:test';
import assert from 'node:assert/strict';
import { pollCandles } from '../src/services/pollCandles.ts';
const tick = () => new Promise(resolve => setImmediate(resolve));

test('late result from previous selection cannot replace the new asset', async () => {
  let resolveOld;
  const received = [];
  const old = pollCandles({ fetch: () => new Promise(r => { resolveOld = r; }),
    onData: d => received.push(d), onError: () => {}, onLoading: () => {} });
  old();
  const current = pollCandles({ fetch: async () => 'ARPAUSDT',
    onData: d => received.push(d), onError: () => {}, onLoading: () => {} });
  await tick();
  resolveOld('BTCUSDT');
  await tick();
  current();
  assert.deepEqual(received, ['ARPAUSDT']);
});

test('polling refreshes without changing asset and retries errors', async t => {
  t.mock.timers.enable({ apis: ['setTimeout'] });
  let calls = 0;
  let errors = 0;
  const received = [];
  const stop = pollCandles({ fetch: async () => { if (++calls === 2) throw Error('offline'); return calls; },
    onData: d => received.push(d), onError: () => errors++, onLoading: () => {} });
  await tick();
  t.mock.timers.tick(60000);
  await tick();
  assert.equal(errors, 1);
  t.mock.timers.tick(60000);
  await tick();
  assert.deepEqual(received, [1, 3]);
  stop();
  t.mock.timers.tick(60000);
  await tick();
  assert.equal(calls, 3);
});
