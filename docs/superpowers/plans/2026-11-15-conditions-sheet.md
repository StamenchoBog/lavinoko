# Conditions Sheet Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the two print options (tour sheet / sheet + forecast) with one two-page "Conditions sheet" whose map is at a fixed 1:25,000 scale centred on the place, with trip-planning content removed and a field observation box added.

**Architecture:** The existing lazy print pipeline stays (`printLoader.ts` → `printing.ts` → `PrintDocument.svelte`). `MapView.svelte`'s off-screen `snapshot()` gains a fixed-scale mode: the caller passes a centre and a ground width, and a pure helper turns that into a MapLibre zoom. The document is restructured into page 1 (map + conditions) and page 2 (detail + observation + emergency).

**Tech Stack:** SvelteKit 3 / Svelte 5 runes, MapLibre GL 6, Playwright (unit + e2e), pnpm.

**Spec:** `docs/superpowers/specs/2026-11-15-conditions-sheet-design.md`

## Global Constraints

- Scale exactly **1:25,000**: ground width (m) = frame width (mm) × 25.
- Map frame width **190 mm**; height about **140 mm** (builder may adjust so page 1 fits); picture about **200 dpi** (≈ 1500 px wide).
- Map centre = the place's `center`; slope layer on, aspect off.
- Every page carries the "not an avalanche danger rating" notice (`s.not_rating`); nothing reads as "safe".
- Each page is exactly one A4 box (210 × 296 mm, `overflow: hidden`), two pages total.
- First-load budget 100 KB gzipped unchanged (`pnpm size`); print code stays lazy.
- Macedonian and English strings for everything new.
- Do not commit; the user commits. End each task with checks passing.

## Review Focus

1. A place whose forecast point falls outside the 4.75 km frame: the map stays at 1:25,000 and the point still appears in the coordinate list (no zoom-out). Test in Task 1.
2. Printing offline or before the map has loaded (`mapHandle.snapshot` is null or throws): the sheet still prints both pages with the "map missing" note. Test in Task 2.
3. Ctrl/Cmd+P and the Print button produce the same two-page document. Test in Task 2.
4. Long Macedonian strings in the observation box and legend do not push page 2 past one A4 page. Test in Task 3 (page height check).
5. Printing twice in a row (second time after closing the dialog) shows a fresh map, not a stale one: `resetAfterPrint` still clears `print.map`. Covered by the existing reset; checked in Task 2.

---

### Task 1: Fixed-scale map picture

**Files:**
- Create: `frontend/src/lib/printScale.ts`
- Modify: `frontend/src/lib/mapHandle.ts` (`SnapshotRequest`)
- Modify: `frontend/src/lib/components/MapView.svelte` (`snapshot()`, about lines 85–150)
- Modify: `frontend/src/lib/printing.ts` (`PRINT_MAP`, snapshot call)
- Test: `frontend/tests/unit/printScale.test.ts`

**Interfaces:**
- Produces: `PRINT_SCALE = 25000`; `zoomForGroundWidth(lat: number, widthPx: number, groundWidthM: number): number` (Web Mercator, 512-px tiles: `log2(40075016.686 · cos(lat) · widthPx / (512 · groundWidthM))`).
- Produces: `SnapshotRequest` gains `fixed?: { center: [number, number]; groundWidthM: number }`. When present, `snapshot()` uses that centre and `zoomForGroundWidth(...)`, and skips both the on-screen framing and the "fit all points" zoom-out. Points outside come back as `null` (existing behaviour).
- Produces: `printing.ts` constants `MAP_MM = { width: 190, height: 140 }` and `PRINT_MAP = { width: 1500, height: round(1500 · 140 / 190) }`.

- [ ] **Step 1: Write the failing test** `tests/unit/printScale.test.ts`:
  - `zoomForGroundWidth(0, 512, 40075016.686)` ≈ `0` (to 1e-9).
  - At lat 41.1, widthPx 1500, groundWidthM `190 * PRINT_SCALE / 1000` (= 4750): the metres per pixel implied by the returned zoom (`40075016.686 · cos(lat) / (512 · 2^z)`) times 1500 equals 4750 to within 0.01 m.
  - Doubling `groundWidthM` lowers the zoom by exactly 1.
- [ ] **Step 2: Run** `cd frontend && pnpm exec playwright test --project=unit tests/unit/printScale.test.ts`. Expected: FAIL (module not found).
- [ ] **Step 3: Implement** `printScale.ts`, then the `fixed` branch in `snapshot()`, then call it from `printPlace()` with `fixed: { center: place.center as [lon, lat], groundWidthM: MAP_MM.width * PRINT_SCALE / 1000 }`. Check the shape of `place.center` in `frontend/src/lib/contract/types.gen.ts` and convert to `[lon, lat]`. Remove `MIN_PRINT_WIDTH_M` if nothing else uses it.
- [ ] **Step 4: Run** the unit test, `pnpm check` and `pnpm lint`. Expected: all pass.

### Task 2: One print, one entry point

**Files:**
- Modify: `frontend/src/lib/printing.ts`, `frontend/src/lib/printLoader.ts`, `frontend/src/lib/state.svelte.ts` (`print.mode`)
- Modify: `frontend/src/lib/components/PrintButton.svelte` (no menu)
- Test: `frontend/tests/e2e/print.spec.ts`

**Interfaces:**
- Consumes: Task 1's `PRINT_MAP` and `fixed` snapshot.
- Produces: `printPlace(): Promise<void>` and `printNow(): Promise<void>`, both without arguments. `PrintMode` and `print.mode` are deleted. Hourly data is always loaded.

- [ ] **Step 1: Rewrite the tests** in `print.spec.ts`:
  - "the print document is not loaded until Print is used": clicking the button `Print` (no menu item) gives `printed === 1` and 2 `.print-doc .page`.
  - "Ctrl+P on a place prints the conditions sheet": 2 pages.
  - "prints without a map": with `window.__noMap = true` set in an init script, and `printing.ts` treating it as a null snapshot (a test hook kept in `printing.ts`), there are still 2 pages and the text of `s.map_missing` is shown. If adding a test hook is unwanted, block `**/data/basemap/**` with `page.route` instead and assert the same.
- [ ] **Step 2: Run** `pnpm exec playwright test --project=e2e tests/e2e/print.spec.ts`. Expected: FAIL (a menu item still exists, 1 page on Ctrl+P).
- [ ] **Step 3: Implement.** The button calls `printNow()` directly and keeps its busy label `s.print_preparing`. Remove `mode` from `PrintDocument.svelte` (always 2 pages).
- [ ] **Step 4: Run** the print e2e, `pnpm check` and `pnpm lint`. Expected: pass.

### Task 3: Page 1 (map and conditions) and page 2 (detail, observation, emergency)

**Files:**
- Modify: `frontend/src/lib/components/print/PrintDocument.svelte`
- Modify: `frontend/src/lib/components/print/PrintMap.svelte`
- Modify: `frontend/src/lib/i18n.ts` (both languages)
- Test: `frontend/tests/e2e/print.spec.ts`

**Interfaces:**
- Consumes: Task 2's two-page document, `MapPicture` (unchanged).
- Produces: `PrintMap` props `{ pic: MapPicture | null; labels: string[] }`, with legend, north arrow and scale text inside the figure.

**Strings** (exact copy, mk / en):
- `doc_sheet`: 'Лист со услови' / 'Conditions sheet'
- `doc_forecast`: 'Детали и набљудување' / 'Detail and observation'
- `map_scale`: '1:25 000 при печатење во 100 %' / '1:25 000 when printed at 100 %'
- `slope_legend`: the slope classes the slope layer already draws. Reuse the existing legend strings from `TerrainTab.svelte`/`i18n.ts` rather than writing new ones.
- `emergency_line`: '112: итни случаи и спасување во планина, бесплатно од секој телефон. Детали на стр. 2.' / '112: emergencies and mountain rescue, free from any phone. Details on page 2.'
- `obs_title`: 'Набљудување на терен' / 'Field observation'
- `obs_when`: 'Датум и час' / 'Date and time'; `obs_where`: 'Место или координати' / 'Place or coordinates'; `obs_elev`: 'Висина' / 'Elevation'; `obs_aspect`: 'Експозиција (заокружете)' / 'Aspect (circle)'; `obs_seen`: 'Што видовте' / 'What you saw'
- Delete: `plan_date`, `plan_start`, `plan_back`, `plan_route`, `sheet_plan`, `sheet_group`, `sheet_turnaround`, `sheet_contact`, `gear_title`, `gear_items`, `print_sheet`, `print_sheet_hint`, `print_full`, `print_full_hint`, `notes_title`. Keep `signs_*`, `call_*`, `burial`, `sheet_112`, `sheet_other`, `map_points`.

- [ ] **Step 1: Write the failing tests** (en, `place=kozuf`):
  - page 1 contains 'Conditions sheet', '1:25 000 when printed at 100 %' and the emergency line, and does not contain 'Turnaround time' or 'Gear'.
  - page 2 contains 'Field observation', every `signs_items` entry as a tick box, and 'Points on the map'.
  - Each `.print-doc .page` has `scrollHeight <= clientHeight` (nothing cut off). Emulate print media with `page.emulateMedia({ media: 'print' })`, and run this for `lang=mk` too.
  - Both pages contain the `not_rating` text.
- [ ] **Step 2: Run** the print e2e. Expected: FAIL.
- [ ] **Step 3: Implement page 1:**
  - order: header, the map frame (190 × 140 mm, picture at exactly the frame width), stats, the by-elevation table plus next days, the emergency line, footer
  - remove the plan box, the gear list and the large emergency column
- [ ] **Step 4: Implement page 2:**
  - order: compact header, chart, days × elevations table, the observation box, the emergency box, about the weather, footer
  - observation box: four labelled write-in fields (`obs_when`, `obs_where`, `obs_elev`, `obs_aspect` with an 8-point compass rose N…NW to circle), the `signs_items` as tick boxes, then write-in lines under `obs_seen`
  - emergency box: `sheet_112`, `call_say` + `call_items`, `burial`, `map_points` with coordinates, `sheet_other`
- [ ] **Step 5: Implement `PrintMap`:**
  - a north arrow (top right) and the slope legend (bottom left), drawn inside the frame
  - `map_scale` under the scale bar
- [ ] **Step 6: Run** the full checks: `pnpm check`, `pnpm lint`, `pnpm exec playwright test` (unit + e2e), `pnpm build && pnpm size`. Expected: all pass, size ≤ 100 KB.
- [ ] **Step 7: Visual check.** Print preview to PDF in Chromium for `kozuf` in mk and en. Confirm the 1:25,000 scale bar measures correctly (1 km = 40 mm) and that both pages are single A4 pages. Update `README.md`/docs wherever they describe the "tour sheet" or two print options.
