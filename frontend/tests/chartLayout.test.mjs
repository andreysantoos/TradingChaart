import assert from 'node:assert/strict';
import { test } from 'node:test';
import { chromium } from 'playwright-core';
import { createServer } from 'vite';

test('windowed chart keeps both scales and draws RSI and MACD through selection changes', async (t) => {
  const server = await createServer({ server: { host: '127.0.0.1', port: 0 }, logLevel: 'error' });
  t.after(() => server.close());
  await server.listen();
  const browser = await chromium.launch();
  t.after(() => browser.close());
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  const candles = Array.from({ length: 160 }, (_, i) => {
    const close = 50 + i + 8 * Math.sin(i / 4);
    return { time: 1700000000 + 900 * i, open: close - 1, high: close + 2,
      low: close - 2, close, volume: 100 + i, is_complete: true };
  });
  await page.route('**/api/**', route => {
    const { pathname: path, searchParams } = new URL(route.request().url());
    const json = path.endsWith('/candles') ? { candles: searchParams.get('timeframe') === '1d' ? candles.slice(-10) : candles }
      : path.endsWith('/symbols') ? [] : {};
    return route.fulfill({ json });
  });
  await page.goto(server.resolvedUrls.local[0]);
  assert.equal(await page.locator('.brand-title').innerText(), 'TrandingChaart');
  await page.locator('.legend-values').waitFor();
  const scale = page.getByTitle('Alternar entre Escala Linear e Logarítmica');
  const toggle = async (name) => {
    await page.getByTitle('Configurar Indicadores Técnicos').click();
    await page.locator('.indicator-card').filter({ hasText: name }).getByRole('button').click();
    await page.locator('.modal-header button').click();
  };
  // Each native pane has a plot cell between its left and right axis cells.
  const plots = page.locator('.main-chart-canvas tr').filter({ has: page.locator('td:nth-child(2) canvas') });
  const hasColor = ({canvas, rgb}) => {
    const pixels = canvas.getContext('2d').getImageData(0, 0, canvas.width, canvas.height).data;
    for (let i = 0; i < pixels.length; i += 4)
      if (rgb.every((v, channel) => Math.abs(v - pixels[i + channel]) <= 5)) return true;
    return false;
  };
  const assertDrawn = async (row, rgb) => {
    const canvas = plots.nth(row).locator('td:nth-child(2) canvas').first();
    await canvas.waitFor();
    await page.waitForFunction(hasColor, { canvas: await canvas.elementHandle(), rgb }, { timeout: 5000 });
  };
  await page.setViewportSize({ width: 740, height: 480 });
  await page.waitForFunction(() => {
    const chart = document.querySelector('.main-chart-canvas table').getBoundingClientRect();
    const controls = document.querySelector('.rotation-control-panel').getBoundingClientRect();
    return chart.right <= innerWidth + 1 && chart.bottom <= innerHeight + 1 && controls.right <= innerWidth;
  }, null, { timeout: 5000 });
  const priceCanvas = plots.first().locator('td:nth-child(2) canvas').first();
  const plot = await priceCanvas.boundingBox();
  const change = page.locator('.legend-change strong');
  const checkChange = async (index) => {
    const previous = candles[index - 1];
    const percent = previous ? 100 * (candles[index].close - previous.close) / previous.close : null;
    const expected = percent === null ? '—'
      : (percent > 0 ? '+' : '') + percent.toFixed(2).replace('.', ',') + '%';
    assert.equal(await change.innerText(), expected);
  };
  await checkChange(candles.length - 1);
  await page.mouse.dblclick(plot.x + plot.width / 2, plot.y + plot.height / 2);
  const seen = new Set();
  for (const fraction of [0.002, 0.24, 0.53]) {
    const oldTime = await page.locator('.legend-time').innerText();
    await page.mouse.move(plot.x + plot.width * fraction, plot.y + plot.height / 2);
    await page.waitForFunction(old => document.querySelector('.legend-time').innerText !== old, oldTime);
    const volume = await page.locator('.legend-values strong').last().innerText();
    const index = candles.findIndex(c => c.volume === Number(volume));
    assert.ok(index >= 0 && index < candles.length - 1);
    seen.add(index);
    await checkChange(index);
  }
  assert.ok(seen.has(0));
  assert.equal(seen.size, 3);
  await page.locator('.brand-title').hover();
  await checkChange(candles.length - 1);
  const handle = await priceCanvas.elementHandle();
  const expectRedraw = async (action) => {
    const before = await priceCanvas.evaluate(canvas => canvas.toDataURL());
    await action();
    await page.waitForFunction(({ canvas, before }) => canvas.toDataURL() !== before,
      { canvas: handle, before }, { timeout: 5000 });
  };
  await expectRedraw(() => scale.click());
  assert.equal(await scale.innerText(), 'LOG');
  await expectRedraw(() => scale.click());
  assert.equal(await scale.innerText(), 'LIN');
  await priceCanvas.hover({ force: true });
  await expectRedraw(() => page.mouse.wheel(0, -200));
  await toggle('MACD');
  await assertDrawn(1, [255, 109, 0]);
  await toggle('RSI');
  await assertDrawn(1, [233, 30, 99]);
  await assertDrawn(2, [255, 109, 0]);
  await page.getByRole('button', { name: '1w', exact: true }).click();
  await assertDrawn(2, [255, 109, 0]);
  await page.getByRole('button', { name: '1d', exact: true }).click();
  await page.getByText('RSI requer 15 candles').waitFor();
  await page.getByText('Sinal do MACD requer 34 candles').waitFor();
  await page.getByRole('button', { name: '15m', exact: true }).click();
  await assertDrawn(1, [233, 30, 99]);
  await toggle('RSI');
  await assertDrawn(1, [255, 109, 0]);
  await toggle('MACD');
  await page.getByRole('button', { name: '1h', exact: true }).click();
  await page.locator('.legend-values').waitFor();
  assert.deepEqual(errors, []);
});
