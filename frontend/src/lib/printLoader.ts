// The small, always-loaded entry to printing. The print code itself (document, chart, map
// frame, QR encoder) is fetched on the first print.
import type { PrintMode } from './printing';
import { currentPlace, print } from './state.svelte';

export function printNow(mode: PrintMode): Promise<void> {
  return import('./printing').then((m) => m.printPlace(mode));
}

/** Ctrl/Cmd+P on a place: print its document (with a fresh map picture) instead of the screen. */
export function onPrintKey(e: KeyboardEvent) {
  if (!(e.ctrlKey || e.metaKey) || e.altKey || e.key.toLowerCase() !== 'p' || !currentPlace()) return;
  e.preventDefault();
  printNow('sheet');
}

/** Printing from the browser menu can't wait for code to load: that print shows the panel, and
 *  the document is fetched so the next one is complete. */
export function onBeforePrint() {
  if (!print.doc && currentPlace()) import('./components/print/PrintDocument.svelte').then((m) => (print.doc = m.default));
}
