import { expect, test } from '@playwright/test';

// One type scale for the whole panel, like the printed sheet: five sizes, three weights.
// (Charts and the map draw their own labels and are not counted.)
async function scale(page: import('@playwright/test').Page) {
  return page.evaluate(() => {
    const sizes = new Set<string>(), weights = new Set<string>();
    for (const el of document.querySelectorAll('.column *')) {
      if (el.closest('svg, .print-doc')) continue;
      const r = el.getBoundingClientRect();
      if (!r.width || !r.height) continue;
      if (![...el.childNodes].some((n) => n.nodeType === 3 && n.textContent!.trim())) continue;
      const cs = getComputedStyle(el);
      sizes.add(cs.fontSize);
      weights.add(cs.fontWeight);
    }
    return { sizes: [...sizes].sort(), weights: [...weights].sort() };
  });
}

for (const [name, url] of [['overview', '/?lang=en'], ['weather', '/?lang=en&place=kozuf'], ['terrain', '/?lang=en&place=kozuf&tab=terrain']] as const) {
  test(`${name}: at most five text sizes and three weights`, async ({ page }) => {
    await page.goto(url);
    await expect(page.locator('.panel h1, .panel h2').first()).toBeVisible();
    for (const d of await page.locator('.panel details').all()) await d.evaluate((el) => ((el as HTMLDetailsElement).open = true));
    const { sizes, weights } = await scale(page);
    expect(sizes.length, sizes.join(', ')).toBeLessThanOrEqual(5);
    expect(weights.length, weights.join(', ')).toBeLessThanOrEqual(3);
  });
}
