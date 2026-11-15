import type { Compass, WeatherPoint } from './types';

/** Fixed decimals, "–" for missing values, and never "-0". */
export function num(v: number | null | undefined, digits = 0): string {
  if (v === null || v === undefined) return '–';
  const s = Number(v).toFixed(digits);
  return /^-0(\.0+)?$/.test(s) ? s.slice(1) : s;
}

/** "14.11. 14:38" in Skopje time, the same in every browser and language. */
export function skopjeTime(iso: string): string {
  const f = new Intl.DateTimeFormat('en-GB', {
    timeZone: 'Europe/Skopje', day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false
  });
  const o = Object.fromEntries(f.formatToParts(new Date(iso)).map((x) => [x.type, x.value]));
  return `${o.day}.${o.month}. ${o.hour}:${o.minute}`;
}

function skopjeParts(d: Date) {
  const f = new Intl.DateTimeFormat('en-GB', {
    timeZone: 'Europe/Skopje', year: 'numeric', day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false
  });
  return Object.fromEntries(f.formatToParts(d).map((x) => [x.type, x.value]));
}

/**
 * Index of the current hour in an hourly series of Skopje times ("2026-11-15T16:00"), so the
 * "now" line moves with the clock instead of staying where it was when the forecast was issued.
 * Before the series starts or after it ends, the nearest end; `fallback` if there are no times.
 */
export function currentHourIndex(times: string[], now = new Date(), fallback = 0): number {
  if (!times.length) return fallback;
  const o = skopjeParts(now);
  const stamp = `${o.year}-${o.month}-${o.day}T${o.hour === '24' ? '00' : o.hour}:00`;
  let i = 0;
  while (i + 1 < times.length && times[i + 1]! <= stamp) i++;
  return i;
}

/** Forecasts are issued on a fixed rhythm, as Alpine services do: 08:00 and 17:00 Skopje time. */
const ISSUE_HOURS = [8, 17];

/** "15.11. 08:00": the next scheduled issue after `now`. */
export function nextIssue(now = new Date()): string {
  for (let h = 0; h < 48; h++) {
    const d = new Date(now.getTime() + h * 3600e3);
    const o = skopjeParts(d);
    if (ISSUE_HOURS.includes(Number(o.hour)) && d > now) return `${o.day}.${o.month}. ${o.hour}:00`;
  }
  return '';
}

/** The latest scheduled issue at or before `now` (Skopje changes time by whole hours). */
export function previousIssue(now = new Date()): Date {
  const hour = Math.floor(now.getTime() / 3600e3) * 3600e3;
  for (let h = 0; h < 48; h++) {
    const d = new Date(hour - h * 3600e3);
    if (ISSUE_HOURS.includes(Number(skopjeParts(d).hour))) return d;
  }
  return new Date(hour);
}

/** The pipeline gets this long to publish a scheduled issue, and may publish this much early. */
const ISSUE_GRACE_MS = 3600e3;

/**
 * True when a newer forecast should exist than the one shown: judged from the data's age,
 * so it also catches a weak connection where the browser still reports being online.
 */
export function missedIssue(issuedIso: string, now = new Date()): boolean {
  const expected = previousIssue(new Date(now.getTime() - ISSUE_GRACE_MS));
  return Date.parse(issuedIso) < expected.getTime() - ISSUE_GRACE_MS;
}

/** "Сре 11.11." from "2026-11-11". */
export function dayLabel(date: string, weekdays: string[]): string {
  const d = new Date(date + 'T00:00:00Z');
  return `${weekdays[d.getUTCDay()]} ${d.getUTCDate()}.${d.getUTCMonth() + 1}.`;
}

export const COMPASS_DEG: Record<Compass, number> = { N: 0, NE: 45, E: 90, SE: 135, S: 180, SW: 225, W: 270, NW: 315 };

export const byHeight = (pts: WeatherPoint[]) => [...pts].sort((a, b) => b.elevation - a.elevation);

/**
 * No snow on the ground (model), none in the last 72 h and none forecast in the next 72 h. Then there
 * is nothing for wind, rain or warming to act on, and the weather alerts stay silent by design; the
 * page says so instead of "nothing notable", which would read as calm weather on a stormy ridge.
 */
export const snowFree = (p: WeatherPoint): boolean =>
  p.now.model_snow_depth_cm === 0 && p.past72.snow_cm === 0 && p.next72.snow_cm === 0;

/** Ridge wind that moves snow and is hard going on a ridge: the backend's strong-wind threshold (T["strong_wind_kmh"]). */
export const STRONG_WIND_KMH = 50;
