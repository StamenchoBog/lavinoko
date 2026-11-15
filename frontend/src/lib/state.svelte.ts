import { replaceState } from '$app/navigation';
import { STRINGS } from './i18n';
import type { Component } from 'svelte';
import type { MapPicture } from './mapHandle';
import type { HourlyPoint, Lang, Place, Source, TerrainMeta, Weather } from './types';

function savedLang(): Lang {
  try {
    const v = localStorage.getItem('lang');
    return v === 'en' || v === 'mk' ? v : 'mk';
  } catch {
    return 'mk';
  }
}

export const ui = $state({
  lang: 'mk' as Lang,
  tab: 'weather' as 'weather' | 'terrain',
  layer: 'slope' as 'slope' | 'aspect' | 'ates',
  draftAtes: false, // ?draft=ates: draft terrain classes for review with guides, not public
  relief: true,
  contours: true,
  inspect: null as { lat: number; lon: number } | null, // tapped map point (point inspector)
  place: null as string | null, // selected place id; null = country overview
  point: null as string | null, // selected forecast point within the place
  error: false,
  highContrast: false, // bright-snow mode: full ink on pure white
  followed: [] as string[]
});

/** What the app fetched. Only ever replaced whole, never edited in place, so it stays raw:
 *  no deep proxies over thousands of forecast values. */
class Data {
  meta = $state.raw<TerrainMeta | null>(null);
  weather = $state.raw<Weather | null>(null);
  sources = $state.raw<Source[]>([]);
  /** Places by id, rebuilt only when a new forecast arrives. */
  placesById = $derived(new Map<string, Place>(this.weather?.places.map((p) => [p.id, p]) ?? []));
}
export const data = new Data();

/** Printing: what the print document shows (set when printing, reset after). The document
 *  component itself is loaded with its code on the first print. */
class Print {
  doc = $state.raw<Component | null>(null);
  map = $state.raw<MapPicture | null>(null);
  hourly = $state.raw<HourlyPoint[] | null>(null);
}
export const print = new Print();

const FOLLOW_KEY = 'lavinoko.followed';
export function loadFollowed() {
  try {
    ui.followed = JSON.parse(localStorage.getItem(FOLLOW_KEY) ?? '[]');
  } catch {
    ui.followed = [];
  }
}
export function toggleFollow(id: string) {
  const follow = !ui.followed.includes(id);
  ui.followed = follow ? [...ui.followed, id] : ui.followed.filter((x) => x !== id);
  // Following means "I want this offline": ask the browser not to clear stored data under pressure
  // (Safari otherwise drops it after 7 days without use). Called from the tap, which some browsers require.
  if (follow) navigator.storage?.persist?.().catch(() => {});
  try {
    localStorage.setItem(FOLLOW_KEY, JSON.stringify(ui.followed));
  } catch {
    /* private mode: not remembered */
  }
}

export function currentPlace() {
  return (ui.place && data.placesById.get(ui.place)) || null;
}

/** Select a place (or null for the overview) and keep it in the address bar for sharing. */
export function selectPlace(id: string | null) {
  ui.place = id;
  const place = currentPlace();
  ui.point = place ? ([...place.points].sort((a, b) => b.elevation - a.elevation)[0]?.id ?? null) : null;
  ui.tab = 'weather';
  // eslint-disable-next-line svelte/prefer-svelte-reactivity -- only passed to replaceState
  const url = new URL(location.href);
  if (id) url.searchParams.set('place', id);
  else url.searchParams.delete('place');
  // eslint-disable-next-line svelte/no-navigation-without-resolve -- same page, only the query string changes
  replaceState(url, {});
}

const CONTRAST_KEY = 'lavinoko.contrast';
/** The user's own choice if they made one, otherwise the phone's "increase contrast" setting. */
export function initContrast() {
  let saved: string | null = null;
  try {
    saved = localStorage.getItem(CONTRAST_KEY);
  } catch {
    /* private mode */
  }
  ui.highContrast = saved ? saved === 'high' : matchMedia('(prefers-contrast: more)').matches;
}
export function setContrast(high: boolean) {
  ui.highContrast = high;
  try {
    localStorage.setItem(CONTRAST_KEY, high ? 'high' : 'normal');
  } catch {
    /* private mode: not remembered */
  }
}

export function t() {
  return STRINGS[ui.lang];
}

export function initLang(params: URLSearchParams) {
  const p = params.get('lang');
  ui.lang = p === 'en' || p === 'mk' ? p : savedLang();
}

export function setLang(lang: Lang) {
  ui.lang = lang;
  try {
    localStorage.setItem('lang', lang);
  } catch {
    /* private mode: language just isn't remembered */
  }
}
