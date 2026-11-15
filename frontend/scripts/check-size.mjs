// Fails when the first page load is over budget: the HTML plus every script and stylesheet the
// browser must fetch before the page runs, measured gzipped (as GitHub Pages serves them).
// Code loaded later with import() (the map library, PMTiles) and the data files do not count.
// Run after `pnpm run build`.
import { existsSync, readFileSync } from 'node:fs';
import { dirname, join, relative, resolve } from 'node:path';
import { gzipSync } from 'node:zlib';

const BUDGET = 100 * 1024;
const root = resolve(process.argv[2] ?? 'build');
const indexFile = join(root, 'index.html');
if (!existsSync(indexFile)) {
  console.error(`${relative('.', indexFile)} not found: run \`pnpm run build\` first.`);
  process.exit(1);
}

const html = readFileSync(indexFile, 'utf-8');
const files = new Map([[indexFile, gzipSync(html).length]]);
const queue = [];

/** A local URL from the page or a script, as a path under build/. */
function local(url, from) {
  if (/^(https?:)?\/\//.test(url) || url.startsWith('data:')) return null;
  return url.startsWith('/') ? join(root, url) : resolve(dirname(from), url);
}

for (const [tag] of html.matchAll(/<(link|script)\b[^>]*>/gi)) {
  const rel = tag.match(/\brel="([^"]+)"/i)?.[1]?.toLowerCase();
  const url = tag.match(/\b(?:href|src)="([^"]+)"/i)?.[1];
  if (!url) continue;
  if (/^<script\b/i.test(tag) || rel === 'modulepreload' || rel === 'stylesheet') queue.push(local(url, indexFile));
}
// SvelteKit starts the app from an inline script: import("./_app/immutable/entry/start.js") etc.
for (const [, url] of html.matchAll(/import\(\s*["']([^"']+\.js)["']\s*\)/g)) queue.push(local(url, indexFile));

// Follow static imports (not import()): those load before the page can run.
while (queue.length) {
  const file = queue.pop();
  if (!file || files.has(file)) continue;
  if (!existsSync(file)) {
    console.error(`Referenced but missing: ${relative(root, file)}`);
    process.exit(1);
  }
  const text = readFileSync(file, 'utf-8');
  files.set(file, gzipSync(text).length);
  if (!file.endsWith('.js')) continue;
  for (const [, url] of text.matchAll(/(?:^|[;\s}])(?:import|export)\s*(?:[\w$*{}\s,]+from\s*)?["']([^"']+)["']/g)) {
    queue.push(local(url, file));
  }
}

const total = [...files.values()].reduce((a, b) => a + b, 0);
const kb = (n) => `${(n / 1024).toFixed(1)} KB`;
for (const [file, size] of [...files].sort((a, b) => b[1] - a[1])) {
  console.log(`${kb(size).padStart(9)}  ${relative(root, file)}`);
}
console.log(`${kb(total).padStart(9)}  total gzipped, budget ${kb(BUDGET)}`);
if (total > BUDGET) {
  console.error(`First page load is ${kb(total - BUDGET)} over budget.`);
  process.exit(1);
}
