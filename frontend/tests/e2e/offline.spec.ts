import { expect, test, type BrowserContext, type Page } from '@playwright/test';

// Offline behaviour of the production build: the situations a skier meets on a chairlift.

const WEATHER = '**/data/weather.json';

/** Open the site once online and wait until the offline worker has installed and taken control. */
async function firstVisit(page: Page) {
  await page.goto('/?lang=en');
  await page.evaluate(async () => {
    await navigator.serviceWorker.ready;
    if (!navigator.serviceWorker.controller) {
      await new Promise((r) => navigator.serviceWorker.addEventListener('controllerchange', r, { once: true }));
    }
  });
}

async function issuedUtc(context: BrowserContext): Promise<string> {
  const r = await context.request.get('/data/weather.json');
  return (await r.json()).issued_utc;
}

/** A clock right after the saved forecast was issued, so it counts as current. */
async function freshClock(page: Page) {
  const issued = Date.parse(await issuedUtc(page.context()));
  await page.clock.install({ time: issued + 30 * 60e3 });
}

test('opens with the saved forecast offline after a single online visit', async ({ page, context }) => {
  await freshClock(page);
  await firstVisit(page);
  await context.setOffline(true);
  await page.reload();
  await expect(page.locator('.updated')).toContainText('Issued');
  await expect(page.getByRole('status')).toContainText('No connection');
});

test('slow connection: the saved forecast shows within 4 s instead of waiting for the network', async ({ page, context }) => {
  await freshClock(page);
  await firstVisit(page);
  let held = 0;
  await context.route(WEATHER, async (route) => {
    held++;
    await new Promise((r) => setTimeout(r, 10_000));
    await route.continue().catch(() => {});
  });
  const t0 = Date.now();
  await page.reload({ waitUntil: 'commit' });
  await expect(page.locator('.updated')).toContainText('Issued', { timeout: 4_000 });
  expect(Date.now() - t0).toBeLessThan(4_000);
  expect(held, 'the slow route must have been hit, or this test proves nothing').toBeGreaterThan(0);
});

test('a forecast that missed its scheduled update is flagged, and replaced when the late network answers', async ({ page, context }) => {
  const saved = await issuedUtc(context);
  // Clock: well after the next scheduled issue, so the saved copy is out of date.
  const now = Date.parse(saved) + 20 * 3600e3;
  await page.clock.install({ time: now });
  await firstVisit(page);

  const newer = new Date(now - 30 * 60e3).toISOString();
  await context.route(WEATHER, async (route) => {
    await new Promise((r) => setTimeout(r, 5_000));
    const response = await route.fetch();
    const body = await response.json();
    await route.fulfill({ response, json: { ...body, issued_utc: newer } });
  });
  await page.reload({ waitUntil: 'commit' });

  const notice = page.getByRole('status').filter({ hasText: 'newer forecast' });
  await expect(notice).toBeVisible({ timeout: 4_000 });
  await expect(notice).toBeHidden({ timeout: 10_000 });
  // Later requests may still be waiting in the slow route: drop them, or they fail the next test.
  await context.unrouteAll({ behavior: 'ignoreErrors' });
});

test('following a place asks the browser to keep stored data', async ({ page }) => {
  await page.addInitScript(() => {
    const w = window as unknown as { persistCalls: number };
    w.persistCalls = 0;
    navigator.storage.persist = async () => {
      w.persistCalls++;
      return true;
    };
  });
  await page.goto('/?lang=en&place=korab');
  await page.getByRole('button', { name: 'Follow' }).click();
  await expect.poll(() => page.evaluate(() => (window as unknown as { persistCalls: number }).persistCalls)).toBeGreaterThan(0);
});
