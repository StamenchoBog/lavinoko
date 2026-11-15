import { expect, test, type Page } from '@playwright/test';

// Gloved hands: every control on a phone must be at least 48 × 48 CSS px (WCAG 2.5.5 asks 44).
// Links inside running text are exempt, as in WCAG.

const MIN = 48;

/** Controls on screen smaller than MIN in either direction, described for the failure message. */
async function smallTargets(page: Page): Promise<string[]> {
  return page.evaluate((min) => {
    const sel = 'button, a[href], summary, input:not([type=hidden]), select, textarea, [role=tab], [tabindex]:not([tabindex="-1"])';
    const out: string[] = [];
    for (const found of document.querySelectorAll<HTMLElement>(sel)) {
      // A checkbox or radio inside a <label> is tapped anywhere on the label: that is the target.
      const el = (found.tagName === 'INPUT' && found.closest('label')) || found;
      const r = el.getBoundingClientRect();
      const style = getComputedStyle(el);
      if (r.width === 0 || r.height === 0 || style.visibility === 'hidden') continue;
      if (r.bottom < 0 || r.top > innerHeight || r.right < 0 || r.left > innerWidth) continue;
      if (el.closest('.print-doc, .sr-only')) continue;
      // Inline link in a sentence: exempt.
      if (el.tagName === 'A' && getComputedStyle(el).display === 'inline' && el.parentElement?.closest('p, li, small, span')) continue;
      // Rounded: the map places markers at sub-pixel positions, so 48 px can measure 47.9.
      if (Math.round(r.width) < min || Math.round(r.height) < min) {
        const name = (el.getAttribute('aria-label') ?? el.textContent ?? '').trim().replace(/\s+/g, ' ').slice(0, 30);
        out.push(`${el.tagName.toLowerCase()}.${[...el.classList].join('.')} "${name}" ${Math.round(r.width)}×${Math.round(r.height)}`);
      }
    }
    return out;
  }, MIN);
}

async function allTargets(page: Page): Promise<string[]> {
  const found = new Set<string>();
  const scan = async () => (await smallTargets(page)).forEach((s) => found.add(s));
  // The panel scrolls: check what is reachable in it, not only its first screen.
  const panel = page.locator('.panel');
  const steps = await panel.evaluate((el) => Math.ceil(el.scrollHeight / el.clientHeight));
  for (let i = 0; i < steps; i++) {
    await panel.evaluate((el, n) => el.scrollTo(0, n * el.clientHeight), i);
    await scan();
  }
  await panel.evaluate((el) => el.scrollTo(0, 0));
  return [...found];
}

test.beforeEach(async ({ page }) => {
  await page.route('https://api.open-meteo.com/**', (r) => r.abort());
});

test('overview: all controls at least 48 px', async ({ page }) => {
  await page.goto('/?lang=en');
  await page.locator('.maplibregl-canvas').waitFor();
  await page.locator('.place-marker').first().waitFor();
  expect(await allTargets(page)).toEqual([]);
});

test('place, weather tab: all controls at least 48 px', async ({ page }) => {
  await page.goto('/?lang=en&place=korab');
  await page.locator('.wx-marker').first().waitFor();
  expect(await allTargets(page)).toEqual([]);
});

test('place, terrain tab: all controls at least 48 px', async ({ page }) => {
  await page.goto('/?lang=en&place=korab&tab=terrain');
  await page.locator('.maplibregl-canvas').waitFor();
  expect(await allTargets(page)).toEqual([]);
});

test('point on the map: all controls at least 48 px', async ({ page }) => {
  await page.goto('/?lang=en');
  await page.locator('.maplibregl-canvas').waitFor();
  await page.mouse.click(200, 160);
  await expect(page.getByRole('region', { name: 'Point on the map' })).toBeVisible();
  expect(await smallTargets(page)).toEqual([]);
});
