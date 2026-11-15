// Puts the small committed test data (tests/fixtures/data) into static/data, for CI or a fresh
// checkout without backend output. Real data already in static/data is left alone unless --force.
import { cpSync, existsSync, rmSync } from 'node:fs';

const from = 'tests/fixtures/data';
const to = 'static/data';
const force = process.argv.includes('--force');

if (existsSync(to) && !force) {
  console.error(`${to} already exists (real backend data?). Leaving it as it is; pass --force to replace it.`);
  process.exit(1);
}
rmSync(to, { recursive: true, force: true });
cpSync(from, to, { recursive: true, filter: (src) => !src.endsWith('README.md') });
console.log(`Copied ${from} to ${to}.`);
