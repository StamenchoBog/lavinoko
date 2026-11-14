# What backcountry skiers and ski resorts need

Checked 2026-11-14. What people look at before going out, what they want alerts for, print and carry
offline — and what LavinOko does about it.

## Findings

**Backcountry skiers and freeriders**
- 86–92 % check the avalanche forecast and change plans because of it (Colorado survey 2026; New Hampshire study 2023). The weather forecast is the next most-used source; trip-description sites dominate for snowshoers and hikers, many of whom don't know a forecast exists (Mount Seymour, BC).
- People **don't retain** the forecast details, even at the trailhead (Swiss field study, ISSW 2023). What isn't simple and carried along is forgotten.
- Users react to **uncertainty** information when it is shown (ISSW 2024).
- Trip planning tools are used for **slope-angle maps**; instructors call a **printed slope-angle map with the route** essential gear because it needs no battery (CalTopo guides).

**Ski resort snow safety / patrol**
- Early-morning check (2:30–6:20): **overnight new snow (24 h)**, **wind** ("an inch of snow, a foot of wind"), temperature and snow density, and the **72-hour outlook** before storms; a short resort-specific briefing goes to the teams.
- Wind with snow drives avalanche control; wind alone can, too.

**Alerts**
- Avalanche centres offer per-region e-mail and text alerts when conditions change (Utah); SLF pushes only unscheduled bulletins.
- No service shows **how much forecast models agree** — users only see one answer.

**Offline**
- The Avalanche Canada app stores forecasts for the field and syncs observations when back online; map apps let you keep areas for offline use.

## What LavinOko does (built)

| Need | In LavinOko |
|---|---|
| Highly accurate alerts | An alert appears only when **2 of 3 independent models** (ICON-EU, GFS, Météo-France) agree; "serious" only if 2 rate it serious. Each alert says "2 of 3 models agree"; snow shows the range across models. Wind alone never "serious"; wind only flagged when there is snow to move. |
| Morning check (patrol) | Place summary shows **last 24 h**: new snow, peak ridge wind, minimum temperature. |
| Simple, retained | Summary first (level → concern → slopes/elevation → why), at most three items, every symbol with a word. |
| My places | **Follow** places: they come first in the list; their hourly data is kept for offline use. |
| Print / carry | Print button next to the place name. **Tour sheet on 1 page** (default) or **sheet + detailed forecast on 2 pages**. The sheet: slope-angle map of exactly the view on screen, with scale bar, north arrow and legend; conditions, elevations and the next days; emergency numbers (112 — also for mountain rescue, answered by the Crisis Management Center ЦУК; police 192, fire 193, ambulance 194), coordinates of forecast points for rescuers, blank plan fields (route, group, turnaround time, who knows the plan), gear reminder; one line of required credits. |
| Offline | Installable app; app, last forecast, terrain layers and viewed map areas work without signal. Clear notice when offline; **warning when the forecast is older than 24 h**. |

## Next (needs hosting or partners)

- **Alert delivery** (e-mail, push, SMS) for followed places — only on a level change, not on every update.
- **Resort morning briefing**: a one-page/short message per resort at 06:00 with overnight snow and wind, for patrol.
- **Station data** to verify the models, then alert on measured values.
- Route drawing and GPX on the tour sheet.

## Sources

- [Colorado avalanche center survey (Colorado Sun, 2026)](https://coloradosun.com/2026/07/09/colorado-avalanche-center-survey/)
- [Avalanche safety practices, New Hampshire (WEM 2023)](https://doi.org/10.1016/j.wem.2023.07.001)
- [Retention and use of avalanche forecast information (ISSW 2023)](https://arc.lib.montana.edu/snow-science/objects/ISSW2023_P2.56.pdf)
- [Users' response to uncertainty in avalanche forecasts (ISSW 2024)](https://arc.lib.montana.edu/snow-science/objects/ISSW2024_O12.3.pdf)
- [Snowshoers and winter hikers, Mount Seymour BC (2025)](https://www.sciencedirect.com/science/article/pii/S2213078025001148)
- [A morning doing avalanche control (Inlander)](https://www.inlander.com/snowlander/a-morning-doing-avalanche-control-reveals-dedication-and-professionalism-from-patrollers-tasked-with-keeping-skiers/article_345a0c1b-9343-5b73-bb0c-71da6eced116.html)
- [Meet the people who keep the slopes safe (Park City)](https://parkcitymag.com/outdoors/2020/12/meet-the-people-who-keep-the-slopes-safe)
- [A day in the life of a snow safety director (Fall Line)](https://www.fall-line.co.uk/day-life-snow-safety-director-frank-coffey/)
- [Avalanche hazard mitigation (Palisades Tahoe)](https://blog.palisadestahoe.com/operations/avalanche-hazard-mitigation-squaw-alpine/)
- [Utah Avalanche Center — advisory e-mail and text alerts](https://utahavalanchecenter.org/avalanche-advisory-email)
- [Avalanche Canada app (Google Play)](https://play.google.com/store/apps/details?id=ca.avalanche.mobile.v2&hl=en_CA)
- [Mountain Information Network FAQ](https://avalanche.ca/mountain-information-network/faq)
- [CalTopo for backcountry skiing (Granite Alpine Lab)](https://granitealpinelab.com/caltopo-for-backcountry-skiing/)
- [Free slope-angle maps on your phone (Alpenflo)](https://alpenflo.com/journal/free-slope-angle-maps-for-your-phone)
- [Open-Meteo forecast and ensemble APIs](https://open-meteo.com/en/docs/ensemble-api)
- [Telephone numbers in North Macedonia (Wikipedia)](https://en.wikipedia.org/wiki/Telephone_numbers_in_North_Macedonia)
- [Balkans emergency numbers](https://www.thebalkanguide.com/practical/emergency-numbers-balkans/)
