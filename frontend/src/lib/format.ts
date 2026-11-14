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

/** "Сре 11.11." from "2026-11-11". */
export function dayLabel(date: string, weekdays: string[]): string {
  const d = new Date(date + 'T00:00:00Z');
  return `${weekdays[d.getUTCDay()]} ${d.getUTCDate()}.${d.getUTCMonth() + 1}.`;
}

export const COMPASS_DEG: Record<Compass, number> = { N: 0, NE: 45, E: 90, SE: 135, S: 180, SW: 225, W: 270, NW: 315 };

export const byHeight = (pts: WeatherPoint[]) => [...pts].sort((a, b) => b.elevation - a.elevation);

/** Ink or white, whichever reads better on an [r, g, b] background (WCAG relative luminance). */
export function textOn(rgb: number[]): string {
  const lin = (c: number) => ((c /= 255) <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4);
  const L = 0.2126 * lin(rgb[0]) + 0.7152 * lin(rgb[1]) + 0.0722 * lin(rgb[2]);
  const ink = 0.0204; // luminance of #17283a
  return (L + 0.05) / (ink + 0.05) >= 1.05 / (L + 0.05) ? '#17283a' : '#ffffff';
}
