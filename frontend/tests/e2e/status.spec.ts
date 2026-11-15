import { expect, test, type Locator, type Page } from '@playwright/test';

// Notices about the data (out of date, models missing, offline) must stay on screen whatever the
// user does with the panel: scroll it, or open a point on the map.

/** A clock long after the saved forecast was issued, so the "newer forecast" notice shows. */
async function outdatedClock(page: Page) {
  const r = await page.context().request.get('/data/weather.json');
  const issued = Date.parse((await r.json()).issued_utc);
  await page.clock.install({ time: issued + 20 * 3600e3 });
}

/** Visible, inside the window, and not covered by anything else at its centre. */
async function expectUncovered(notice: Locator) {
  await expect(notice).toBeVisible();
  await expect(notice).toBeInViewport({ ratio: 1 });
  const onTop = await notice.evaluate((el) => {
    const r = el.getBoundingClientRect();
    const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
    return !!hit && el.contains(hit);
  });
  expect(onTop, 'something covers the notice').toBe(true);
}

const notice = (page: Page) => page.getByRole('status').filter({ hasText: 'is overdue' });

test.describe('phone', () => {
  test('the notice stays on screen while a point on the map is open', async ({ page }) => {
    await page.route('https://api.open-meteo.com/**', (r) => r.abort()); // the inspector's live weather
    await outdatedClock(page);
    await page.goto('/?lang=en');
    await expectUncovered(notice(page));

    await page.locator('.maplibregl-canvas').waitFor();
    // The notice must leave the map buttons free (48 px for gloves): no overlap at all, not just at the centre.
    const box = (await notice(page).boundingBox())!;
    const buttons = (await page.locator('.maplibregl-ctrl-top-right .maplibregl-ctrl-group').first().boundingBox())!;
    expect(box.x + box.width, 'the notice overlaps the map buttons').toBeLessThanOrEqual(buttons.x);

    await page.mouse.click(200, 160); // the map, above the panel
    await expect(page.getByRole('region', { name: 'Point on the map' })).toBeVisible();
    await expectUncovered(notice(page));
  });
});

test.describe('desktop', () => {
  test.use({ viewport: { width: 1280, height: 720 }, isMobile: false, hasTouch: false });

  test('the notice stays on screen when the panel is scrolled to the end', async ({ page }) => {
    await outdatedClock(page);
    await page.goto('/?lang=en&place=korab');
    await expect(page.getByRole('heading', { level: 1 })).toContainText('Korab');
    const panel = page.locator('.panel');
    const overflows = await panel.evaluate((el) => el.scrollHeight > el.clientHeight + 100);
    expect(overflows, 'the panel must be long enough to scroll, or this test proves nothing').toBe(true);

    await panel.evaluate((el) => el.scrollTo(0, el.scrollHeight));
    await expectUncovered(notice(page));
  });
});

test('notices about the data are read politely, not as interrupting alerts', async ({ page }) => {
  // A forecast over 24 hours old, issued while the models could not be compared.
  await page.route('**/data/weather.json', async (route) => {
    const response = await route.fetch();
    const body = await response.json();
    await route.fulfill({ response, json: { ...body, health: { ...body.health, consensus: false } } });
  });
  const r = await page.context().request.get('/data/weather.json');
  await page.clock.install({ time: Date.parse((await r.json()).issued_utc) + 30 * 3600e3 });
  await page.goto('/?lang=en');

  await expect(page.getByRole('status').filter({ hasText: 'more than 24 hours old' })).toBeVisible();
  await expect(page.getByRole('status').filter({ hasText: 'Not enough models' })).toBeVisible();
  await expect(page.getByRole('alert')).toHaveCount(0);
});
