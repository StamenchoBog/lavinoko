import { expect, test, type Page } from '@playwright/test';

// High contrast for bright snow: secondary text becomes full ink on pure white. It can be switched
// on by hand (remembered) and follows the phone's "increase contrast" setting.

const toggle = (page: Page) => page.getByRole('button', { name: 'High contrast' });
const secondaryText = (page: Page) => page.locator('.updated').evaluate((el) => getComputedStyle(el).color);
const heading = (page: Page) => page.getByRole('heading', { level: 1 }).evaluate((el) => getComputedStyle(el).color);

test('the high-contrast button turns secondary text into full ink, and is remembered', async ({ page }) => {
  await page.goto('/?lang=en');
  await expect(toggle(page)).toHaveAttribute('aria-pressed', 'false');
  expect(await secondaryText(page)).not.toBe(await heading(page));

  await toggle(page).click();
  await expect(toggle(page)).toHaveAttribute('aria-pressed', 'true');
  expect(await secondaryText(page)).toBe(await heading(page));
  expect(await page.locator('.panel').evaluate((el) => getComputedStyle(el).backgroundColor)).toBe('rgb(255, 255, 255)');

  await page.reload();
  await expect(toggle(page)).toHaveAttribute('aria-pressed', 'true');
  expect(await secondaryText(page)).toBe(await heading(page));
});

test('high contrast is on when the phone asks for more contrast', async ({ page }) => {
  await page.emulateMedia({ contrast: 'more' });
  await page.goto('/?lang=en');
  await expect(toggle(page)).toHaveAttribute('aria-pressed', 'true');
  expect(await secondaryText(page)).toBe(await heading(page));
});
