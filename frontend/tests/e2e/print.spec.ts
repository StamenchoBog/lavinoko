import { expect, test } from '@playwright/test';

// The print document and its code load only when someone prints, then the browser's print runs.

test.use({ viewport: { width: 1280, height: 720 }, isMobile: false, hasTouch: false });

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    (window as unknown as { printed: number }).printed = 0;
    window.print = () => void (window as unknown as { printed: number }).printed++;
  });
});
const printed = (page: import('@playwright/test').Page) => page.evaluate(() => (window as unknown as { printed: number }).printed);

test('the print document is not loaded until Print is used', async ({ page }) => {
  await page.goto('/?lang=en&place=korab');
  await expect(page.getByRole('heading', { level: 1 })).not.toHaveText('');
  await expect(page.locator('.print-doc')).toHaveCount(0);

  await page.getByRole('button', { name: 'Print' }).click();
  await page.getByRole('menuitem', { name: /Sheet \+ detailed forecast/ }).click();
  await expect.poll(() => printed(page)).toBe(1);
  await expect(page.locator('.print-doc .page')).toHaveCount(2);
});

test('Ctrl+P on a place prints the tour sheet', async ({ page }) => {
  await page.goto('/?lang=en&place=korab');
  await expect(page.getByRole('button', { name: 'Print' })).toBeVisible();
  await page.keyboard.press('Control+p');
  await expect.poll(() => printed(page)).toBe(1);
  await expect(page.locator('.print-doc .page')).toHaveCount(1);
});
