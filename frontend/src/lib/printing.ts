// The conditions sheet: page 1 map and conditions, page 2 detail, field observation and emergency.
// This module and the print document are loaded only when someone prints (see printLoader).
import { tick } from 'svelte';
import { loadData } from './data';
import { byHeight } from './format';
import { mapHandle } from './mapHandle';
import { frameCenter, PRINT_SCALE, withTimeout } from './printScale';
import { currentPlace, print } from './state.svelte';

/** Map frame on paper, in mm. */
export const MAP_MM = { width: 190, height: 155 };
/** Print map picture size in CSS pixels (about 200 dpi); its aspect ratio equals the map frame. */
export const PRINT_MAP = { width: 1500, height: Math.round((1500 * MAP_MM.height) / MAP_MM.width) };

export async function printPlace(): Promise<void> {
  const place = currentPlace();
  if (!place) return;
  const points = byHeight(place.points);
  const lonLats = points.map((p): [number, number] => [p.lon, p.lat]);
  const [doc, pic, hourly] = await Promise.all([
    import('./components/print/PrintDocument.svelte').then((m) => m.default),
    (mapHandle.snapshot?.({
      ...PRINT_MAP,
      center: frameCenter(lonLats, place.center),
      groundWidthM: (MAP_MM.width * PRINT_SCALE) / 1000,
      points: lonLats
    }) ?? Promise.resolve(null)).catch(
      () => null
    ),
    // Never viewed offline: a stalled request must not block printing; page 2 then has no chart.
    withTimeout(loadData('hourly', `hourly/${place.id}.json`).then((d) => d?.points ?? null), 10000, null)
  ]);
  print.doc = doc;
  print.map = pic;
  print.hourly = hourly;
  await tick();
  const img = document.querySelector<HTMLImageElement>('.print-doc img');
  if (img) await img.decode().catch(() => {});
  window.print();
}

/** After any print (button or Ctrl+P), forget the picture so a later print never shows a stale view. */
export function resetAfterPrint() {
  print.map = null;
  print.hourly = null;
}
