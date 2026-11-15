import { expect, test } from '@playwright/test';

// With no snow anywhere there is nothing for wind, rain or warming to act on: the site says so,
// instead of "nothing notable", which would read as calm weather on a stormy ridge.
async function withSnow(page: import('@playwright/test').Page, snow: boolean) {
  await page.route('**/data/weather.json', async (route) => {
    const response = await route.fetch();
    const body = await response.json();
    for (const p of body.places) {
      p.level = 'none';
      for (const q of p.points) {
        q.flags = [];
        q.now.model_snow_depth_cm = snow ? 40 : 0;
        q.past72.snow_cm = 0;
        q.next72.snow_cm = 0;
      }
    }
    await route.fulfill({ response, json: body });
  });
}

// Requests still in the route when a test ends must not fail it (or the next one).
test.afterEach(async ({ page }) => page.unrouteAll({ behavior: 'ignoreErrors' }));

test('overview without snow anywhere says there is no snow, not that the weather is calm', async ({ page }) => {
  await withSnow(page, false);
  await page.goto('/?lang=en');
  await expect(page.locator('.banner')).toContainText('No snow on the ground or in the forecast');
});

test('overview with snow but no alerts keeps the plain message', async ({ page }) => {
  await withSnow(page, true);
  await page.goto('/?lang=en');
  await expect(page.locator('.banner')).toContainText('Nothing notable in the weather');
});

test('a snow-free place says why there are no weather alerts', async ({ page }) => {
  await withSnow(page, false);
  await page.goto('/?lang=en&place=kozuf');
  await expect(page.locator('.card.calm')).toContainText('No snow on the ground or forecast');
});
