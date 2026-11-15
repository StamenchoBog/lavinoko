// Loading the data files, checked against the contract generated from the backend models.
import { base } from '#lib/paths.ts';
import { dataProblem, type DataName } from './contract/check';
import type { Roots } from './contract/types.gen';
import { DATA_CACHE } from './swcache';

export const dataUrl = (file: string) => `${base}/data/${file}`;

/**
 * Fetch a data file and check it. If it can't be fetched or is invalid (a broken or half-written
 * file), use the last good copy the offline worker stored; null if there is none.
 */
export async function loadData<N extends DataName>(name: N, file: string): Promise<Roots[N] | null> {
  const url = dataUrl(file);
  try {
    const r = await fetch(url);
    if (r.ok) {
      const data: unknown = await r.json();
      const problem = dataProblem(name, data);
      if (!problem) return data as Roots[N];
      console.warn(`Invalid ${file} (${problem}); using the last good copy.`);
    }
  } catch {
    /* offline or not JSON: fall back to the stored copy */
  }
  return lastGood(name, url);
}

async function lastGood<N extends DataName>(name: N, url: string): Promise<Roots[N] | null> {
  try {
    const cached = await (await caches.open(DATA_CACHE)).match(url);
    const data: unknown = await cached?.json();
    return cached && dataProblem(name, data) === null ? (data as Roots[N]) : null;
  } catch {
    return null; // no Cache API (insecure context) or nothing stored
  }
}
