# Conditions sheet (print) — design

**Date:** 2026-11-15 · **Status:** approved

## Intent

People take the printout on tour. The platform is avalanche detection and prediction, not route planning, so
the printout works like an avalanche service's printable bulletin: it carries what the system knows (weather
facts now, a danger rating later) and where the avalanche terrain is, into the field, and gives the reader a
place to record what they observe. Everything that plans a trip is removed.

## Goals

- One print, **"Conditions sheet"**, two A4 pages, for a place.
- A **fixed-scale 1:25,000 map** centred on the place: slope classes, contours, forecast points, grid,
  scale bar, north arrow, legend.
- A structured **field observation box** that feeds the observation programme (2027/28).
- Emergency information kept, but small.

## Non-goals

- Route drawing, GPX, a movable or user-chosen map frame, a choice of scale.
- Trip planning: the plan box (date, start, turnaround, return, group, route, contact) and the gear checklist.
- Printing the overview (it stays the browser's default print of the panel).

## Anti-goals

- Anything on paper that reads as a danger rating or as "safe". The "not an avalanche danger rating" notice
  stays on every page.
- A map whose scale changes with the screen.

## Approaches considered

- **A. Browser renders the map at print time** (chosen, without the movable frame): reuses the existing
  off-screen MapLibre snapshot, works offline for viewed areas, and the reviewed ATES layer or a future danger
  map can go on the same map. Cost: a few seconds on old phones.
- B. Backend pre-renders one map per place: sharpest, but 17 more build outputs to keep current, and nothing
  else in the print needs the backend.
- C. Fixed numbered map sheets: the most files for the least gain now.

## Design

**Print entry.** The Print button prints the conditions sheet directly; the two-option menu goes away.
Ctrl/Cmd+P on a place prints the same document. The hourly series is always loaded for the print.

**Page 1: map and conditions**
- Header as now (brand, place, issued / printed, weather concerns, not-a-rating notice). Document title
  "Conditions sheet" / "Лист со услови".
- Map: full content width (190 mm), 172 mm high, at exactly 1:25,000: ground width = frame width in mm
  × 25 m. Centre = the middle of the place's forecast points (not the place's `center`, which can sit at one
  end: at Kožuf it put the summit point off the map). North up and flat, whatever the screen map shows.
  Slope layer on, aspect off (as now).
  Overlays: degree grid (as now; coordinates match phones and the 112 box), forecast points numbered,
  scale bar, north arrow, slope-class legend, and the text "1:25 000 at 100 % print size".
- Conditions: the five headline stats and the by-elevation table, as now.
- One emergency line: "112: emergencies and mountain rescue, free from any phone" + see page 2.

**Page 2: detail and observation**
- Hour-by-hour chart and the days × elevations table, as now.
- **Field observation box:** date / time, where (place or coordinates), elevation, aspect (compass to
  circle), the alarm signs as tick boxes (existing `signs_items`), free notes lines. Replaces the separate
  signs list and the empty "Field notes" lines.
- Emergency: what to say, burial step, forecast-point coordinates, other numbers (existing strings).
- About the weather (as now). Footer with sources and QR on both pages.

**Removed strings and code:** `plan_*`, `sheet_plan`, `sheet_group`, `sheet_turnaround`, `sheet_contact`,
`gear_title`, `gear_items`, `print_sheet`, `print_sheet_hint`, `print_full`, `print_full_hint`, the
`PrintMode` type and `print.mode`. Gear moves to the education pages when they are written.

## Constraints

- First-load budget (100 KB gzipped) unchanged: print code stays lazily loaded.
- Snapshot at about 200 dpi (190 mm ≈ 1500 px wide); the picture is shown at exactly the frame width.
- Every forecast point must be on the map (true today: every place's points span ≤ 3.2 km; the frame is
  4.75 km wide). If one ever falls outside, the frame stays at 1:25,000 and the point is listed only.
- Both languages; touch, contrast and print e2e tests updated.

## Left to the builder

Exact page-1 map height, the legend's look, the north arrow, and the observation box layout, as long as both
pages stay single A4 pages with nothing cut off.
