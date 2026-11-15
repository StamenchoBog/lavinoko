/// <reference types="@sveltejs/kit" />
/// <reference no-default-lib="true"/>
/// <reference lib="esnext" />
/// <reference lib="webworker" />
// Offline support: app and core data stored on install; forecasts network-first with a short wait,
// and a data file that fails the contract check never replaces the last good copy;
// terrain and base-map tiles kept only as the user views them (no bulk downloading of base-map
// tiles, per OpenFreeMap's terms).
import { version } from '$app/env';
import { assets, immutable, prerendered } from '$app/manifest';
import { DATA_CACHE, responseProblem, staleAppCaches } from '#lib/swcache.ts';

const sw = self as unknown as ServiceWorkerGlobalScope;
/** The site's base path ('' locally, '/<repo>' on GitHub Pages): the worker is registered at the site root. */
const base = new URL(sw.registration.scope).pathname.replace(/\/$/, '');
/** The manifest lists paths relative to the base path. */
const at = (path: string) => `${base}/${path.replace(/^\//, '')}`;
const APP = `app-${version}`;
const DATA = DATA_CACHE;
const TILES = 'tiles-v1';
const MAX_TILES = 4000;
/** On a weak connection, wait this long for fresh data before showing the stored copy. */
const NETWORK_WAIT_MS = 2500;

// App shell: built code, small static files and the prerendered page. Large/generated data is cached at runtime.
const SHELL = [
  ...immutable.map((f) => at(f.path)),
  ...assets.map((f) => at(f.path)).filter((f) => !f.includes('/data/')),
  ...prerendered.map((f) => at(f.path))
];
/** The one page: every navigation (?place=, ?lang=) is served this stored copy. */
const INDEX = `${base}/`;
/**
 * App files are stored without request headers, but the browser asks for module scripts with an
 * `Origin` header; a server that answers with `Vary: Origin` (Vite 8's preview, some CDNs) would make
 * every stored copy miss. Their names change with their content, so the headers never matter.
 */
const SHELL_MATCH: CacheQueryOptions = { ignoreVary: true };
// Small data the page needs to start; stored on install so the very first visit already works offline.
const CORE_DATA = ['weather.json', 'sources.json', 'terrain/metadata.json'].map((f) => `${base}/data/${f}`);

sw.addEventListener('install', (event) => {
  // No skipWaiting(): an update activates once the old version's tabs are closed, so a tab that is
  // still open never asks for chunks of a version whose files have been removed.
  event.waitUntil(
    Promise.all([
      caches.open(APP).then((c) => c.addAll(SHELL)),
      // Missing data (e.g. no forecast built yet) must not stop the app from installing.
      caches.open(DATA).then((c) => Promise.all(CORE_DATA.map((u) => storeIfValid(c, u))))
    ])
  );
});

sw.addEventListener('activate', (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(staleAppCaches(keys, APP).map((k) => caches.delete(k))))
      .then(() => sw.clients.claim())
  );
});

/** Fetch a data file and store it, only if it passes the check. Failures are ignored. */
async function storeIfValid(cache: Cache, url: string): Promise<void> {
  try {
    const response = await fetch(url);
    if ((await responseProblem(response, url)) === null) await cache.put(url, response);
  } catch {
    /* offline or missing: keep what is stored */
  }
}

/** Tell open pages that newer data has been stored, so they can show it. */
async function notify(url: string) {
  for (const client of await sw.clients.matchAll({ type: 'window' })) client.postMessage({ type: 'data-updated', url });
}

/**
 * Network first, but never wait more than NETWORK_WAIT_MS when a stored copy exists. The network
 * request keeps going; if it answers after the stored copy was shown, the pages are told.
 * A failed or invalid answer (error status, broken JSON, wrong shape) is not stored, and the
 * stored copy is served instead when there is one.
 */
function networkFirst(event: FetchEvent, cacheName: string): Promise<Response> {
  const { request } = event;
  return (async () => {
    const cache = await caches.open(cacheName);
    const cached = await cache.match(request);
    let servedCached = false;
    const network = fetch(request).then(async (response) => {
      const problem = await responseProblem(response, request.url);
      if (problem) {
        if (cached) console.warn(`Keeping the stored ${request.url}: ${problem}`);
        return cached ?? response;
      }
      await cache.put(request, response.clone());
      if (servedCached) await notify(request.url);
      return response;
    });
    event.waitUntil(network.catch(() => {}));
    if (!cached) return network;
    const fallback = () => ((servedCached = true), cached);
    const wait = new Promise<Response>((resolve) => setTimeout(() => resolve(fallback()), NETWORK_WAIT_MS));
    return Promise.race([network.catch(fallback), wait]);
  })();
}

/** Stored copy first; fetch and store if missing. */
async function cacheFirst(request: Request, cacheName: string): Promise<Response> {
  const cache = await caches.open(cacheName);
  const cached = await cache.match(request);
  if (cached) return cached;
  const response = await fetch(request);
  if (response.ok) {
    cache.put(request, response.clone());
    trim(cacheName, MAX_TILES);
  }
  return response;
}

/**
 * PMTiles are read with HTTP range requests (206 responses), which the Cache API cannot store as is.
 * Each range is stored as a normal response under a key that includes the range.
 */
async function rangeCacheFirst(request: Request): Promise<Response> {
  const range = request.headers.get('range') ?? '';
  // A query parameter, not a #fragment: the Cache API ignores fragments when matching.
  const key = new Request(`${request.url}${request.url.includes('?') ? '&' : '?'}sw-range=${encodeURIComponent(range)}`);
  const cache = await caches.open(TILES);
  const cached = await cache.match(key);
  if (cached) {
    return new Response(cached.body, {
      status: 206,
      headers: {
        'content-type': cached.headers.get('content-type') ?? 'application/octet-stream',
        'content-range': cached.headers.get('x-content-range') ?? ''
      }
    });
  }
  const response = await fetch(request);
  if (response.status === 206 || response.status === 200) {
    const body = await response.clone().arrayBuffer();
    cache.put(
      key,
      new Response(body, {
        headers: {
          'content-type': response.headers.get('content-type') ?? 'application/octet-stream',
          'x-content-range': response.headers.get('content-range') ?? ''
        }
      })
    );
    trim(TILES, MAX_TILES);
  }
  return response;
}

async function trim(cacheName: string, max: number) {
  const cache = await caches.open(cacheName);
  const keys = await cache.keys();
  for (const k of keys.slice(0, Math.max(0, keys.length - max))) await cache.delete(k);
}

sw.addEventListener('fetch', (event) => {
  const { request } = event;
  if (request.method !== 'GET') return;
  const url = new URL(request.url);

  if (url.origin === sw.location.origin) {
    if (url.pathname.endsWith('.pmtiles')) {
      event.respondWith(rangeCacheFirst(request));
    } else if (url.pathname.includes('/data/')) {
      event.respondWith(networkFirst(event, DATA));
    } else if (request.mode === 'navigate') {
      // One page for every query (?place=, ?lang=): serve the stored copy at once, even on a weak
      // connection. A new version arrives with the next offline worker, not by refetching the page.
      event.respondWith(caches.match(INDEX, SHELL_MATCH).then((r) => r ?? fetch(request)));
    } else if (SHELL.includes(url.pathname)) {
      event.respondWith(caches.match(request, SHELL_MATCH).then((r) => r ?? fetch(request)));
    }
    return;
  }

  // Base map (style, tiles, fonts, sprites): keep what was viewed.
  if (url.hostname === 'tiles.openfreemap.org') {
    event.respondWith(url.pathname.includes('/styles/') ? networkFirst(event, TILES) : cacheFirst(request, TILES));
  }
});

// The page can ask for data to be stored ahead of time (e.g. hourly forecasts of followed places).
sw.addEventListener('message', (event) => {
  const msg = event.data as { type?: string; urls?: string[] };
  if (msg?.type === 'prefetch' && Array.isArray(msg.urls)) {
    const urls = msg.urls;
    event.waitUntil(caches.open(DATA).then((c) => Promise.all(urls.map((u) => storeIfValid(c, u)))));
  }
});
