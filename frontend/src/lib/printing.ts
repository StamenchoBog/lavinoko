// Page 1 is the tour sheet; "full" adds page 2 (hour-by-hour chart, day table, field checklist).
// This module and the print document are loaded only when someone prints (see printLoader).
import { tick } from 'svelte';
import { loadData } from './data';
import { byHeight } from './format';
import { mapHandle } from './mapHandle';
import { currentPlace, print } from './state.svelte';
export type PrintMode = 'sheet' | 'full';

/** Print map picture size in CSS pixels; its aspect ratio equals the map frame on paper (190 × 86 mm). */
const PRINT_MAP = { width: 1600, height: 724 };

export async function printPlace(mode: PrintMode): Promise<void> {
  const place = currentPlace();
  if (!place) return;
  const points = byHeight(place.points);
  const [doc, pic, hourly] = await Promise.all([
    import('./components/print/PrintDocument.svelte').then((m) => m.default),
    (mapHandle.snapshot?.({ ...PRINT_MAP, points: points.map((p) => [p.lon, p.lat]) }) ?? Promise.resolve(null)).catch(
      () => null
    ),
    mode === 'full'
      ? loadData('hourly', `hourly/${place.id}.json`).then((d) => d?.points ?? null)
      : Promise.resolve(null)
  ]);
  print.doc = doc;
  print.mode = mode;
  print.map = pic;
  print.hourly = hourly;
  await tick();
  const img = document.querySelector<HTMLImageElement>('.print-doc img');
  if (img) await img.decode().catch(() => {});
  window.print();
}

/** After any print (button or Ctrl+P), forget the picture so a later print never shows a stale view. */
export function resetAfterPrint() {
  print.mode = 'sheet';
  print.map = null;
  print.hourly = null;
}
