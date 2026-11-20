# Architecture — open decisions

LavinOko is developed locally until it is a polished product; hosting is decided after that.

## What is settled

- **Website:** SvelteKit built to static files (`frontend/`). Runs on any static host.
- **Data pipeline:** Python (`backend/`): terrain layers (PMTiles) and the twice-daily weather forecast.

## Field reports: reuse first

An own report system (form, local store, draft Supabase schema) was built and then removed on 2026-11-15,
before anyone had used it. Following the roadmap, the first winter uses an existing tool (Regobs if it accepts
outside regions, otherwise a plain form), and LavinOko only shows the reports on its map. An own system is
built only once guides and patrol are actually submitting. The removed code is in git history
(last present in commit `f3ab3c7`).

## Also open

- **Hosting the website:** not set up; CI only runs checks. Wherever the site is hosted, it needs the same
  scheduled `backend/weather/fetch_weather.py` run as the archive below (it exits non-zero on unhealthy data).

## Forecast archive

Every forecast run (the blend and each model, ~300 KB gzipped, ~175 MB per October–June season) is committed to a
separate public repository, `lavinoko-archive`. That repository holds only the schedule
([`lavinoko-archive/.github/workflows/fetch.yml`](https://github.com/StamenchoBog/lavinoko-archive/blob/main/.github/workflows/fetch.yml)); it calls
`.github/workflows/forecast.yml` here, which fetches with this repository's code and commits back with the
archive repository's own token. GitHub starts scheduled runs late (hours, on 15 Nov 2026) or drops them, so the
on-time runs at 06:17 and 15:17 UTC are started by a Cloudflare Worker (`workers/archive-trigger/`) through the API (`workflow_dispatch`, with a
fine-grained token that can only start workflows in the archive repository). GitHub's own schedule is the backup:
30 and 90 minutes later, plus one run a month in summer so GitHub never disables it. Every scheduled run fetches only
if nothing is archived yet for the current slot (since 06:00 or 15:00 UTC), so late runs do no harm. Open-Meteo requests are retried on rate limits and outages. The archive repo stays under GitHub's 1 GB guideline for about five seasons; then start
one repository per season, or publish closed seasons to Zenodo.

The archive repository also checks itself once a day (`lavinoko-archive/.github/workflows/check.yml`, script and
tests in `.github/scripts/`): a slot with no file, or one archived late because the Worker did not start it, is
reported in an issue there. It depends on neither this repository nor the Worker, so it still reports when they break.

## Verification

`backend/verify/verify.py` compares the archived forecasts with what happened, per source (the website's blend
and each model) and lead day: temperature hourly, snow and rain as 24-hour sums, and snow and heavy-snow days as
hits and false alarms. Run it on a local clone of the archive:

```sh
cd backend && uv run python verify/verify.py --archive ../../lavinoko-archive/weather --out report.md
```

Until there are measurements, the reference is ERA5 reanalysis (Open-Meteo, ~6 days behind, ~25 km grid). It is
independent of the forecast models but smooths the mountains, so it ranks models and lead times rather than
telling the truth on the mountain. Station data replaces it through `--reference stations.csv` (format in the
script). Ridge-height wind is not verified: there is no reference for it yet.
