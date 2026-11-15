import { expect, test } from '@playwright/test';

// The AutoATES terrain classes are an unvalidated draft for review with guides: never offered to
// normal visitors, and always shown with the draft warning.

test.use({ viewport: { width: 1280, height: 720 }, isMobile: false, hasTouch: false });

test('the draft terrain classes are hidden without ?draft=ates', async ({ page }) => {
  await page.goto('/?lang=en&place=korab&tab=terrain');
  await expect(page.getByRole('button', { name: 'Slope angle' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'ATES (draft)' })).toHaveCount(0);
});

test('with ?draft=ates the classes come with the draft warning', async ({ page }) => {
  await page.goto('/?lang=en&place=korab&tab=terrain&draft=ates');
  await page.getByRole('button', { name: 'ATES (draft)' }).click();
  await expect(page.getByText('DRAFT, not validated.')).toBeVisible();
  await expect(page.getByRole('listitem').filter({ hasText: 'Complex' })).toBeVisible();
});
