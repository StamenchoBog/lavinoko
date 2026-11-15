import AxeBuilder from '@axe-core/playwright';
import { expect, test, type Page } from '@playwright/test';

// Snow glare: text must reach WCAG AAA contrast (7:1, or 4.5:1 for large text), measured on the
// rendered page. The map itself (canvas) is not text and is not checked here.

async function aaaViolations(page: Page): Promise<string[]> {
  const result = await new AxeBuilder({ page })
    .withRules(['color-contrast-enhanced'])
    .exclude('.maplibregl-canvas')
    .exclude('.print-doc')
    .analyze();
  return result.violations.flatMap((v) =>
    v.nodes.map((n) => `${n.target.join(' ')} — ${n.any[0]?.message ?? v.help}`.replace(/\s+/g, ' ').slice(0, 220))
  );
}

/** Check the whole scrollable panel, not just its first screen. */
async function panelViolations(page: Page): Promise<string[]> {
  const found = new Set<string>();
  const panel = page.locator('.panel');
  const steps = await panel.evaluate((el) => Math.ceil(el.scrollHeight / el.clientHeight));
  for (let i = 0; i < steps; i++) {
    await panel.evaluate((el, n) => el.scrollTo(0, n * el.clientHeight), i);
    (await aaaViolations(page)).forEach((v) => found.add(v));
  }
  return [...found];
}

test.beforeEach(async ({ page }) => {
  await page.route('https://api.open-meteo.com/**', (r) => r.abort());
  // Open every collapsible section, so its text is checked too.
  await page.addInitScript(() => {
    new MutationObserver(() => document.querySelectorAll('details:not([open])').forEach((d) => d.setAttribute('open', ''))).observe(
      document,
      { subtree: true, childList: true }
    );
  });
});

test('overview text reaches 7:1', async ({ page }) => {
  await page.goto('/?lang=en');
  await page.locator('.place-marker').first().waitFor();
  expect(await panelViolations(page)).toEqual([]);
});

test('place, weather tab text reaches 7:1', async ({ page }) => {
  await page.goto('/?lang=en&place=korab');
  await page.locator('.wx-marker').first().waitFor();
  expect(await panelViolations(page)).toEqual([]);
});

test('place, terrain tab text reaches 7:1', async ({ page }) => {
  await page.goto('/?lang=en&place=korab&tab=terrain');
  await page.locator('.maplibregl-canvas').waitFor();
  expect(await panelViolations(page)).toEqual([]);
});

test('high contrast: place text reaches 7:1', async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem('lavinoko.contrast', 'high'));
  await page.goto('/?lang=en&place=korab');
  await page.locator('.wx-marker').first().waitFor();
  await expect(page.locator('html')).toHaveAttribute('data-contrast', 'high');
  expect(await panelViolations(page)).toEqual([]);
});

test('aspect legend text reaches 7:1', async ({ page }) => {
  await page.goto('/?lang=en&place=korab&tab=terrain');
  await page.getByRole('button', { name: 'Aspect' }).click();
  expect(await panelViolations(page)).toEqual([]);
});

test('point on the map text reaches 7:1', async ({ page }) => {
  await page.goto('/?lang=en');
  await page.locator('.maplibregl-canvas').waitFor();
  await page.mouse.click(200, 160);
  await expect(page.getByRole('region', { name: 'Point on the map' })).toBeVisible();
  expect(await aaaViolations(page)).toEqual([]);
});
