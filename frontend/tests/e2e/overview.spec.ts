import { expect, test } from '@playwright/test';

test.use({ viewport: { width: 1280, height: 900 }, isMobile: false, hasTouch: false });

test('the list has column headings with units', async ({ page }) => {
  await page.goto('/?lang=en');
  const head = page.locator('.cols-head');
  await expect(head).toContainText('New snow 72 h');
  await expect(head).toContainText('Ridge wind km/h');
});

test('a place named after its range does not repeat the name', async ({ page }) => {
  await page.goto('/?lang=en');
  const row = page.locator('li', { hasText: 'Kožuf' }).filter({ has: page.locator('b', { hasText: /^Kožuf$/ }) });
  await expect(row.locator('.where small')).toHaveText(/^\d+ m$/);
});

test('strong ridge wind stands out from the rest', async ({ page }) => {
  await page.route('**/data/weather.json', async (route) => {
    const response = await route.fetch();
    const body = await response.json();
    body.places.forEach((p: { headline: { wind_next72: { max_kmh: number } } }, i: number) => (p.headline.wind_next72.max_kmh = i === 0 ? 85 : 20));
    await route.fulfill({ response, json: body });
  });
  await page.goto('/?lang=en');
  await expect(page.locator('.wind.strong')).toHaveCount(1);
  await page.unrouteAll({ behavior: 'ignoreErrors' });
});

test('pointing at a place in the list highlights it on the map, with its name', async ({ page }) => {
  await page.goto('/?lang=en');
  await page.locator('.place-marker').first().waitFor({ state: 'attached' });
  const row = page.locator('.panel li button').first();
  const name = (await row.locator('b').textContent())!;
  await row.hover();
  const hot = page.locator('.place-marker.hot');
  await expect(hot).toHaveCount(1);
  await expect(hot.locator('span')).toBeVisible();
  await expect(hot).toHaveAttribute('title', name);
  await page.mouse.move(900, 450);
  await expect(page.locator('.place-marker.hot')).toHaveCount(0);
});
