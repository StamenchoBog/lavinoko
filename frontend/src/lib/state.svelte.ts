import { STRINGS } from './i18n';
import type { Observer, Report } from './reports';
import type { Lang, Source, TerrainMeta, Weather } from './types';

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
  tab: 'weather' as 'weather' | 'terrain' | 'reports',
  layer: 'slope' as 'slope' | 'aspect',
  relief: true,
  contours: true,
  inspect: null as { lat: number; lon: number } | null, // tapped map point (point inspector)
  place: null as string | null, // selected place id; null = country overview
  point: null as string | null, // selected forecast point within the place
  meta: null as TerrainMeta | null,
  weather: null as Weather | null,
  sources: [] as Source[],
  reports: [] as Report[],
  observer: null as Observer | null,
  reportForm: false, // the new-report form is open (map taps then set its point)
  draftPoint: null as { lat: number; lon: number } | null,
  error: false,
  followed: [] as string[],
  // Printing: what the print document shows (set by the Print button, reset after printing).
  printMode: 'sheet' as 'sheet' | 'full',
  printMap: null as import('./mapHandle').MapPicture | null,
  printHourly: null as import('./types').HourlyPoint[] | null
});

const FOLLOW_KEY = 'lavinoko.followed';
export function loadFollowed() {
  try {
    ui.followed = JSON.parse(localStorage.getItem(FOLLOW_KEY) ?? '[]');
  } catch {
    ui.followed = [];
  }
}
export function toggleFollow(id: string) {
  ui.followed = ui.followed.includes(id) ? ui.followed.filter((x) => x !== id) : [...ui.followed, id];
  try {
    localStorage.setItem(FOLLOW_KEY, JSON.stringify(ui.followed));
  } catch {
    /* private mode: not remembered */
  }
}

export function currentPlace() {
  return ui.weather?.places.find((p) => p.id === ui.place) ?? null;
}

/** Select a place (or null for the overview) and keep it in the address bar for sharing. */
export function selectPlace(id: string | null) {
  ui.place = id;
  const place = currentPlace();
  ui.point = place ? [...place.points].sort((a, b) => b.elevation - a.elevation)[0].id : null;
  if (ui.tab !== 'reports') ui.tab = 'weather';
  const url = new URL(location.href);
  if (id) url.searchParams.set('place', id);
  else url.searchParams.delete('place');
  history.replaceState(history.state, '', url);
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
