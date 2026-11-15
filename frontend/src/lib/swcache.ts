// Cache housekeeping for the offline worker (src/service-worker.ts), kept here so it can be tested.
import { dataNameFor, dataProblem } from './contract/check';

/** Forecast, terrain metadata and source register: only copies that pass the data check are kept. */
export const DATA_CACHE = 'data-v1';

/**
 * App-shell caches to delete when a new version activates. The newest previous shell is kept:
 * a tab still running the old version may lazily load one of its chunks (e.g. the map) while offline.
 * `keys` is in creation order, as `caches.keys()` returns it.
 */
export function staleAppCaches(keys: string[], current: string): string[] {
  const old = keys.filter((k) => k.startsWith('app-') && k !== current);
  return old.slice(0, -1);
}

/**
 * Why a data response must not replace the stored copy, or null if it may. Files the page does not
 * check (e.g. the base-map style) only need a successful status. Reads a clone; `response` stays usable.
 */
export async function responseProblem(response: Response, url: string): Promise<string | null> {
  if (!response.ok) return `HTTP ${response.status}`;
  const name = dataNameFor(new URL(url, 'http://localhost').pathname); // the base only resolves a relative URL
  if (!name) return null;
  try {
    return dataProblem(name, await response.clone().json());
  } catch {
    return 'not JSON';
  }
}
