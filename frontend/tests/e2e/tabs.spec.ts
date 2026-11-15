import { expect, test } from '@playwright/test';

// The Weather / Terrain tabs follow the WAI-ARIA tabs pattern, so screen-reader and keyboard users
// get what the roles promise.

test.use({ viewport: { width: 1280, height: 720 }, isMobile: false, hasTouch: false });

test('tabs are named, control a labelled panel, and only the selected one is in the tab order', async ({ page }) => {
  await page.goto('/?lang=en&place=korab');
  const tablist = page.getByRole('tablist');
  await expect(tablist).toHaveAccessibleName(/.+/);

  const weather = page.getByRole('tab', { name: 'Weather' });
  const terrain = page.getByRole('tab', { name: 'Terrain' });
  await expect(weather).toHaveAttribute('aria-selected', 'true');
  await expect(weather).toHaveAttribute('tabindex', '0');
  await expect(terrain).toHaveAttribute('tabindex', '-1');

  const panelId = await weather.getAttribute('aria-controls');
  expect(panelId).toBeTruthy();
  const panel = page.locator(`#${panelId}`);
  await expect(panel).toHaveAttribute('role', 'tabpanel');
  await expect(page.getByRole('tabpanel')).toHaveAccessibleName('Weather');
});

test('arrow keys, Home and End move between tabs and show their panel', async ({ page }) => {
  await page.goto('/?lang=en&place=korab');
  const weather = page.getByRole('tab', { name: 'Weather' });
  const terrain = page.getByRole('tab', { name: 'Terrain' });

  await weather.focus();
  await page.keyboard.press('ArrowRight');
  await expect(terrain).toBeFocused();
  await expect(terrain).toHaveAttribute('aria-selected', 'true');
  await expect(page.getByRole('tabpanel', { name: 'Terrain' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Slope angle' })).toBeVisible();

  await page.keyboard.press('ArrowRight'); // wraps around
  await expect(weather).toBeFocused();
  await page.keyboard.press('End');
  await expect(terrain).toBeFocused();
  await page.keyboard.press('Home');
  await expect(weather).toBeFocused();
  await expect(weather).toHaveAttribute('aria-selected', 'true');
});
