import { expect, test } from '@playwright/test';

// The place view says each number once: the weather message, one table by elevation (with the
// last 24 h), the hour-by-hour chart, and folded detail. Like the printed sheet.

test.use({ viewport: { width: 1280, height: 900 }, isMobile: false, hasTouch: false });

test('no day cards and no separate overnight line: the table carries the last 24 h', async ({ page }) => {
  await page.goto('/?lang=en&place=kozuf');
  const tab = page.locator('.weather');
  await expect(tab).toBeVisible();
  await expect(tab.locator('.strip')).toHaveCount(0);
  await expect(tab.locator('.overnight')).toHaveCount(0);
  await expect(tab.locator('table').first().locator('thead')).toContainText('Last 24 h');
});

test('the new-snow gauge and the long caveat are folded away', async ({ page }) => {
  await page.goto('/?lang=en&place=kozuf');
  const tab = page.locator('.weather');
  await expect(tab.locator('.gauge')).toBeHidden();
  await tab.getByText('New snow and critical amounts').click();
  await expect(tab.locator('.gauge')).toBeVisible();
  const calm = tab.locator('.card.calm');
  if (await calm.count()) {
    await expect(calm.locator('.why')).toBeHidden();
    await calm.getByText('Why?').click();
    await expect(calm.locator('.why')).toBeVisible();
  }
});
