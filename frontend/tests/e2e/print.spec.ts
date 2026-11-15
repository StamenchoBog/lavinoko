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
  await expect.poll(() => printed(page)).toBe(1);
  await expect(page.getByRole('menuitem')).toHaveCount(0);
  await expect(page.locator('.print-doc .page')).toHaveCount(2);
});

test('Ctrl+P on a place prints the conditions sheet', async ({ page }) => {
  await page.goto('/?lang=en&place=korab');
  await expect(page.getByRole('button', { name: 'Print' })).toBeVisible();
  await page.keyboard.press('Control+p');
  await expect.poll(() => printed(page)).toBe(1);
  await expect(page.locator('.print-doc .page')).toHaveCount(2);
});

test('without the map, the sheet still prints both pages', async ({ page }) => {
  await page.route('**/data/basemap/**', (r) => r.abort());
  await page.route('https://tiles.openfreemap.org/**', (r) => r.abort());
  await page.goto('/?lang=en&place=korab');
  await page.getByRole('button', { name: 'Print' }).click();
  await expect.poll(() => printed(page)).toBe(1);
  await expect(page.locator('.print-doc .page')).toHaveCount(2);
});

async function printSheet(page: import('@playwright/test').Page, lang: 'en' | 'mk') {
  await page.goto(`/?lang=${lang}&place=kozuf`);
  await page.getByRole('button', { name: lang === 'en' ? 'Print' : 'Печати' }).click();
  await expect.poll(() => printed(page)).toBe(1);
  await page.emulateMedia({ media: 'print' });
  return page.locator('.print-doc .page');
}

test('page 1 is the map and conditions, with no trip planning', async ({ page }) => {
  const p1 = (await printSheet(page, 'en')).nth(0);
  await expect(p1).toContainText('Conditions sheet');
  await expect(p1).toContainText('1:25 000 when printed at 100 %');
  await expect(p1).toContainText('112 emergencies and mountain rescue, free from any phone. Details on page 2.');
  await expect(p1).not.toContainText('Turnaround time');
  await expect(p1).not.toContainText('Gear');
});

test('page 2 has the field observation box and the emergency details', async ({ page }) => {
  const p2 = (await printSheet(page, 'en')).nth(1);
  await expect(p2).toContainText('Field observation');
  await expect(p2.locator('.obs .tick')).toHaveCount(5);
  await expect(p2).toContainText('Points on the map');
});

for (const lang of ['en', 'mk'] as const) {
  test(`every page fits one A4 page and says it is not a danger rating (${lang})`, async ({ page }) => {
    const pages = await printSheet(page, lang);
    await expect(pages).toHaveCount(2);
    for (let i = 0; i < 2; i++) {
      const pg = pages.nth(i);
      await expect(pg.locator('.rating')).toHaveCount(1);
      const fits = await pg.evaluate((el) => [...el.children].every((c) => c.getBoundingClientRect().bottom <= el.getBoundingClientRect().bottom + 0.5));
      expect(fits, `page ${i + 1} content overflows`).toBe(true);
    }
  });
}

test('a rotated screen map still prints north-up, and the screen keeps its rotation', async ({ page }) => {
  await page.goto('/?lang=en&place=kozuf');
  const rose = page.locator('.rose svg');
  await expect(rose).toBeVisible({ timeout: 15000 });
  await page.locator('.maplibregl-canvas').waitFor({ timeout: 15000 });
  await page.locator('.maplibregl-canvas').focus();
  await page.keyboard.press('Shift+ArrowLeft');
  await expect(rose).not.toHaveAttribute('style', /rotate\(-?0deg\)/);
  // Record every bearing the map takes while printing (the rose follows the map's bearing).
  await page.evaluate(() => {
    const el = document.querySelector('.rose svg')!;
    const seen: string[] = ((window as unknown as { bearings: string[] }).bearings = []);
    new MutationObserver(() => seen.push(el.getAttribute('style') ?? '')).observe(el, { attributes: true });
  });
  await page.getByRole('button', { name: 'Print' }).click();
  await expect.poll(() => printed(page), { timeout: 20000 }).toBe(1);
  const seen = await page.evaluate(() => (window as unknown as { bearings: string[] }).bearings);
  expect(seen.some((st) => /rotate\(-?0deg\)/.test(st)), 'map was north-up while captured').toBe(true);
  await expect(rose).not.toHaveAttribute('style', /rotate\(-?0deg\)/);
});

test('without a map picture the sheet says why, without sending the reader back to Print', async ({ page }) => {
  await page.route('**/data/basemap/**', (r) => r.abort());
  await page.route('https://tiles.openfreemap.org/**', (r) => r.abort());
  await page.goto('/?lang=en&place=korab');
  await page.getByRole('button', { name: 'Print' }).click();
  await expect.poll(() => printed(page)).toBe(1);
  await expect(page.locator('.print-doc')).toContainText('Map not available (offline, not loaded yet, or printed from the browser menu).');
});

test('page 1 says each number once: one table, no headline figures, no day cards', async ({ page }) => {
  const p1 = (await printSheet(page, 'en')).nth(0);
  await expect(p1.locator('.stats, .days')).toHaveCount(0);
  await expect(p1.locator('table')).toHaveCount(1);
  await expect(p1.locator('thead')).toContainText('Last 24 h');
  await expect(p1).toContainText('Freezing level');
  await expect(p1.locator('.sub')).not.toContainText('Kožuf ·');
});

test('credits: short with the map and QR code on page 1, full on page 2', async ({ page }) => {
  const pages = await printSheet(page, 'en');
  await expect(pages.nth(0)).toContainText('© OpenStreetMap contributors');
  await expect(pages.nth(0).locator('.qr')).toHaveCount(1);
  await expect(pages.nth(1).locator('.qr')).toHaveCount(0);
  await expect(pages.nth(1)).toContainText('Copernicus WorldDEM-30');
  await expect(pages.nth(1).locator('.cols2 > div:last-child')).toContainText('About the data');
});

for (const lang of ['en', 'mk'] as const) {
  test(`the sheet uses at most four text sizes (${lang})`, async ({ page }) => {
    await printSheet(page, lang);
    const sizes = await page.evaluate(() => {
      const out = new Set<string>();
      for (const el of document.querySelectorAll('.print-doc *')) {
        if (el.closest('svg') || el.closest('.qr')) continue;
        if ([...el.childNodes].some((n) => n.nodeType === 3 && n.textContent!.trim())) out.add(getComputedStyle(el).fontSize);
      }
      return [...out].sort();
    });
    expect(sizes.length, sizes.join(', ')).toBeLessThanOrEqual(4);
  });
}

test('the observation box has room to write: fields at least 11 mm high', async ({ page }) => {
  const p2 = (await printSheet(page, 'en')).nth(1);
  const mm = await p2.locator('.obs .fields > div').first().evaluate((el) => el.getBoundingClientRect().height / (96 / 25.4));
  expect(mm).toBeGreaterThanOrEqual(10.9);
  await expect(p2.locator('.obs .lines span')).toHaveCount(4);
});

test('the map has fine grid ticks for reading a position', async ({ page }) => {
  test.setTimeout(60000);
  await page.goto('/?lang=en&place=kozuf');
  await page.locator('.maplibregl-canvas').waitFor();
  await page.waitForTimeout(4000);
  await page.getByRole('button', { name: 'Print' }).click();
  await expect.poll(() => printed(page), { timeout: 20000 }).toBe(1);
  await expect(page.locator('.print-doc figure img')).toHaveCount(1);
  expect(await page.locator('.print-doc .minor').count()).toBeGreaterThan(20);
});
