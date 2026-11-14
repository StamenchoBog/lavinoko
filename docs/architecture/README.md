# Architecture — open decisions

LavinOko is developed locally until it is a polished product; hosting is decided after that.

## What is settled

- **Website:** SvelteKit built to static files (`frontend/`). Runs on any static host.
- **Data pipeline:** Python (`backend/`): terrain layers (PMTiles) and the twice-daily weather forecast.
- **Field reports:** invited observers only (guides, ski patrol, mountain rescue, forecasters).
  Reports are shown immediately, labelled by role and organisation, never by name or e-mail.
  Photos are re-encoded in the browser, which removes GPS position and camera details.

## What is open: where reports are stored

Reports are currently **switched off** in the page (`REPORTS_ENABLED = false`); the code is kept for later.

The page talks only to the `ReportStore` interface in `frontend/src/lib/reports.ts`.
Today the only implementation is **local** (IndexedDB in the browser, test sign-in by role), clearly
labelled in the page. Choosing hosting means adding one implementation of that interface.

| Option | Notes |
|---|---|
| Supabase (hosted or self-hosted) | Postgres + login by e-mail link + photo storage. Draft schema with access rules: `option-supabase-schema.sql`. Free tier is enough for a pilot. |
| Own server | e.g. a small API + Postgres on a grant-funded VPS. Same data model as the draft schema. |

Questions to settle before choosing: who administers observer accounts, where personal data
(observer e-mail addresses) is hosted (North Macedonia's personal data protection law applies),
and how reports are backed up.

## Also open

- **Hosting the website and scheduled forecast updates:** not set up; CI only runs checks. Wherever the site
  is hosted, `backend/weather/fetch_weather.py` must run on a schedule (it exits non-zero on unhealthy data).
