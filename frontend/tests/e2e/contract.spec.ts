import { expect, test, type Page } from '@playwright/test';

// A broken forecast file (half-written, wrong shape) must never replace a good one on the phone.

const WEATHER = '**/data/weather.json';

async function firstVisit(page: Page) {
  await page.goto('/?lang=en');
  await page.evaluate(async () => {
    await navigator.serviceWorker.ready;
    if (!navigator.serviceWorker.controller) {
      await new Promise((r) => navigator.serviceWorker.addEventListener('controllerchange', r, { once: true }));
    }
  });
}

const storedIssued = (page: Page) =>
  page.evaluate(async () => {
    const r = await (await caches.open('data-v1')).match('/data/weather.json');
    return r ? ((await r.json()) as { issued_utc: string }).issued_utc : null;
  });

for (const [what, body] of [
  ['cut off', '{"issued_utc": "2026-11-15T07:00:00+00:00", "places": ['],
  ['the wrong shape', JSON.stringify({ issued_utc: '2026-11-15T07:00:00+00:00', places: 'none' })]
] as const) {
  test(`a forecast file that is ${what} keeps the last good copy`, async ({ page, context }) => {
    const issued = (await (await context.request.get('/data/weather.json')).json()).issued_utc as string;
    await page.clock.install({ time: Date.parse(issued) + 30 * 60e3 });
    await firstVisit(page);
    expect(await storedIssued(page)).toBe(issued);

    let served = 0;
    await context.route(WEATHER, (route) => {
      served++;
      return route.fulfill({ status: 200, contentType: 'application/json', body });
    });
    await page.reload();
    await expect(page.getByRole('tab', { name: 'Weather' })).toBeVisible();
    await expect(page.locator('.updated')).toContainText('Issued');
    expect(served, 'the broken file must have been served, or this test proves nothing').toBeGreaterThan(0);
    expect(await storedIssued(page)).toBe(issued);
  });
}

test.describe('without the offline worker', () => {
  test.use({ serviceWorkers: 'block' });

  test('an invalid forecast and no stored copy: the page opens on terrain instead of breaking', async ({ page, context }) => {
    await context.route(WEATHER, (route) => route.fulfill({ status: 200, contentType: 'application/json', body: '{"places": 1}' }));
    await page.goto('/?lang=en');
    await expect(page.getByRole('tab', { name: 'Terrain' })).toHaveAttribute('aria-selected', 'true');
    await expect(page.getByRole('tab', { name: 'Weather' })).toHaveCount(0);
    await expect(page.locator('.updated')).not.toContainText('did not load');
  });
});
