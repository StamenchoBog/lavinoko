# Learning from the Swiss avalanche service (SLF / White Risk)

Checked 2026-11-14. What the Swiss do well, what research says goes wrong, and what LavinOko takes from it.

## How the Swiss service works

| Aspect | SLF practice |
|---|---|
| Rhythm | Main bulletin daily at **17:00**, valid until 17:00 next day. **08:00 update** in winter when the evening bulletin shows level 3+ anywhere (sometimes at level 2). Outside winter only after significant snowfall. Every bulletin shows its issue/update time. |
| Structure | Zoomable danger map plus, per region, four parts in fixed order: **A** danger level → **B** avalanche-prone locations (aspect + elevation) → **C** avalanche problems (max. three) → **D** description. Separate "Snowpack and weather" section. |
| Regions | Warning regions with the same level, locations, problems and text are merged into one danger region. |
| Problems | Dry (new snow, wind slab, old snow) and wet (wet snow, gliding snow) assessed separately; only problems that substantially contribute are listed. |
| Products | Interactive bulletin, printable PDF (full and per region), icon map (levels only), snow maps, measured values (stations), AvaBlog, archive. |
| Channels | Website, White Risk app (free; route planning needs a licence), radio and TV interviews in winter, the national natural-hazards portal and MeteoSwiss app, social media (supplementary), data service/API. |
| Alerts | Push notifications only for **unscheduled** bulletins (extra winter bulletin, summer bulletin after snowfall). Radio/TV coverage added when danger rises. |
| Observations | Reports via White Risk or the website (not social media). Since 2025/26: mark the **release point** on a map, size and type, photos/video. Every report appears on the public map of current avalanches and feeds the forecasters. |
| Languages | Danger map and descriptions in four languages at 17:00; snowpack/weather text in German first, translations by 18:00. |

## What research says users get wrong

- Users rate the danger level as important but **hard to understand** (Engeset et al. 2018, Norway).
- Most users, **including experienced ones, don't know the problem icons by heart**; when two problems are shown, most can't say why (Slovenian bulletin redesign study).
- Some less experienced users **didn't realise the bulletin was about danger** — they read it as a snow report.
- Experienced users and guides rate danger lower than the bulletin; snowshoers higher (Winkler & Techel, Swiss surveys).
- Danger levels must be **applied consistently** between services, or users crossing borders are misled (Techel et al. 2018).

## What LavinOko does with it

**Taken over**
- Fixed rhythm 08:00 / 17:00, with "issued … next update …" on every page.
- Place view opens with a summary in the A→B→C→D order: level → main concern → where (aspect rose + elevation) → why it matters. At most three concerns, most severe first.
- Icon map: places coloured by level on the country map, plus a banner summing up the country.
- Printable place view; archive of every forecast as issued.

**Done differently / better**
- **Symbols are never alone:** every level shows symbol + word; every concern is named in words with one plain sentence on why it matters.
- **Always says what it is:** every page states "a weather forecast, not an avalanche danger rating" until real danger ratings exist.
- **Both languages at the same moment** (generated together, no translation delay).
- **Everything free** — no licence for any feature.
- **Open:** open-source code and openly readable data files; sources and licences shown in the app.
- **Alerts that don't train people to ignore them:** wind alone is never "serious", and wind is flagged only when there is snow to move.
- "New since your last visit" marker on places whose level rose.

**Later (needs hosting or more data)**
- Push notifications for unscheduled changes only (as SLF).
- Measured values from stations; snow maps.
- Observation reports on a map, shown publicly at once; for avalanches the release point (via a reused tool first, see `docs/architecture/`).
- Machine-readable bulletin feed in the European standard format (CAAML) for other apps.
- Region merging and real danger levels once trained forecasters issue them (after a shadow season, winter 2028/29 at the earliest).

## Sources

- [SLF – The avalanche bulletin](https://www.slf.ch/en/avalanche-bulletin-and-snow-situation/about-the-avalanche-bulletin/the-avalanche-bulletin/)
- [SLF – Publication times and validity](https://www.slf.ch/en/avalanche-bulletin-and-snow-situation/about-the-avalanche-bulletin/publication-times-and-validity/)
- [SLF – Products](https://www.slf.ch/en/avalanche-bulletin-and-snow-situation/about-the-avalanche-bulletin/products/)
- [SLF – Typical avalanche problems](https://www.slf.ch/en/avalanche-bulletin-and-snow-situation/about-the-avalanche-bulletin/typical-avalanche-problems/)
- [SLF – Media used](https://www.slf.ch/en/avalanche-bulletin-and-snow-situation/about-the-avalanche-bulletin/media-used/)
- [SLF – New to White Risk: avalanche reporting made easy](https://www.slf.ch/en/news/new-to-white-risk-avalanche-reporting-made-easy/)
- [White Risk – App Store](https://apps.apple.com/us/app/white-risk/id339374432)
- [Engeset et al. 2018 – Communicating public avalanche warnings: what works?](https://nhess.copernicus.org/articles/18/2537/2018/nhess-18-2537-2018.pdf)
- [Increasing awareness of avalanche danger: redesigning a bulletin](https://link.springer.com/chapter/10.1007/978-3-030-60114-0_26)
- [Users' rating of the Swiss avalanche forecast](https://www.academia.edu/26662079/Users_Rating_of_the_Swiss_Avalanche_Forecast)
- [Techel et al. 2018 – Spatial consistency and bias in avalanche forecasts](https://www.researchgate.net/publication/324066899_Spatial_consistency_and_bias_in_avalanche_forecasts_-_a_case_study_in_the_European_Alps)
