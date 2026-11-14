/// <reference types="@sveltejs/kit" />
/// <reference no-default-lib="true"/>
/// <reference lib="esnext" />
/// <reference lib="webworker" />
// Offline support: app stored on install; forecasts network-first; terrain and base-map tiles
// kept only as the user views them (no bulk downloading of base-map tiles, per OpenFreeMap's terms).
import { build, files, version } from '$service-worker';

const sw = self as unknown as ServiceWorkerGlobalScope;
const APP = `app-${version}`;
const DATA = 'data-v1';
const TILES = 'tiles-v1';
const MAX_TILES = 4000;

// App shell: built code plus small static files. Large/generated data is cached at runtime instead.
const SHELL = [...build, ...files.filter((f) => !f.includes('/data/'))];

sw.addEventListener('install', (event) => {
  event.waitUntil(caches.open(APP).then((c) => c.addAll(SHELL)).then(() => sw.skipWaiting()));
});

sw.addEventListener('activate', (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((k) => k.startsWith('app-') && k !== APP).map((k) => caches.delete(k))))
      .then(() => sw.clients.claim())
  );
});

/** Network first, falling back to the last stored copy. */
async function networkFirst(request: Request, cacheName: string): Promise<Response> {
  const cache = await caches.open(cacheName);
  try {
    const response = await fetch(request);
    if (response.ok) cache.put(request, response.clone());
    return response;
  } catch {
    const cached = await cache.match(request);
    if (cached) return cached;
    throw new Error('offline and not cached');
  }
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
      event.respondWith(networkFirst(request, DATA));
    } else if (SHELL.includes(url.pathname)) {
      event.respondWith(caches.match(request).then((r) => r ?? fetch(request)));
    } else if (request.mode === 'navigate') {
      // The page itself: fresh when online, stored copy when offline.
      event.respondWith(networkFirst(request, APP).catch(() => caches.match(`${url.origin}${SHELL.find((f) => f.endsWith('/')) ?? '/'}`) as Promise<Response>));
    }
    return;
  }

  // Base map (style, tiles, fonts, sprites): keep what was viewed.
  if (url.hostname === 'tiles.openfreemap.org') {
    event.respondWith(url.pathname.includes('/styles/') ? networkFirst(request, TILES) : cacheFirst(request, TILES));
  }
});

// The page can ask for data to be stored ahead of time (e.g. hourly forecasts of followed places).
sw.addEventListener('message', (event) => {
  const msg = event.data as { type?: string; urls?: string[] };
  if (msg?.type === 'prefetch' && Array.isArray(msg.urls)) {
    event.waitUntil(caches.open(DATA).then((c) => Promise.all(msg.urls!.map((u) => c.add(u).catch(() => {})))));
  }
});
