import { readFileSync } from 'node:fs';
import { expect, test } from '@playwright/test';

// Colour tokens that the contrast scan (tests/e2e/contrast.spec.ts) cannot see: icons and symbols
// are not text, but WCAG 1.4.11 still asks 3:1 against what they sit on.

const css = readFileSync(new URL('../../src/routes/+page.svelte', import.meta.url), 'utf-8');

function token(name: string): string {
  const m = css.match(new RegExp(`--${name}:\\s*(#[0-9a-fA-F]{6})`));
  if (!m?.[1]) throw new Error(`token --${name} not found`);
  return m[1];
}

function luminance(hex: string): number {
  const c = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255);
  const [r, g, b] = c.map((x) => (x <= 0.03928 ? x / 12.92 : ((x + 0.055) / 1.055) ** 2.4)) as [number, number, number];
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function ratio(a: string, b: string): number {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x) as [number, number];
  return (hi + 0.05) / (lo + 0.05);
}

test('attention symbol stands out 3:1 from the panel and from white', () => {
  expect(ratio(token('signal'), token('snow'))).toBeGreaterThanOrEqual(3);
  expect(ratio(token('signal'), '#ffffff')).toBeGreaterThanOrEqual(3);
});

test('serious symbol stands out 3:1 from the panel', () => {
  expect(ratio(token('serious'), token('snow'))).toBeGreaterThanOrEqual(3);
});
