// Page 1 is the tour sheet; "full" adds page 2 (hour-by-hour chart, day table, field checklist).
import { tick } from 'svelte';
import { base } from '$app/paths';
import { byHeight } from './format';
import { mapHandle } from './mapHandle';
import { currentPlace, ui } from './state.svelte';
import type { HourlyPoint } from './types';

export type PrintMode = 'sheet' | 'full';

/** Print map picture size in CSS pixels; its aspect ratio equals the map frame on paper (190 × 86 mm). */
export const PRINT_MAP = { width: 1600, height: 724 };

export async function printPlace(mode: PrintMode): Promise<void> {
  const place = currentPlace();
  if (!place) return;
  const points = byHeight(place.points);
  const [pic, hourly] = await Promise.all([
    (mapHandle.snapshot?.({ ...PRINT_MAP, points: points.map((p) => [p.lon, p.lat]) }) ?? Promise.resolve(null)).catch(
      () => null
    ),
    mode === 'full'
      ? fetch(`${base}/data/hourly/${place.id}.json`)
          .then((r) => r.json())
          .then((d) => d.points as HourlyPoint[])
          .catch(() => null)
      : Promise.resolve(null)
  ]);
  ui.printMode = mode;
  ui.printMap = pic;
  ui.printHourly = hourly;
  await tick();
  const img = document.querySelector<HTMLImageElement>('.print-doc img');
  if (img) await img.decode().catch(() => {});
  window.print();
}

/** After any print (button or Ctrl+P), forget the picture so a later print never shows a stale view. */
export function resetAfterPrint() {
  ui.printMode = 'sheet';
  ui.printMap = null;
  ui.printHourly = null;
}
