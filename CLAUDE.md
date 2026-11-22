# LavinOko

Free, open avalanche information for North Macedonia: a SvelteKit static site (`frontend/`) fed by a Python data
pipeline (`backend/`). Proof of concept: it shows terrain and weather, **not avalanche danger**. See `README.md` for
layout and how to run it, `docs/architecture/README.md` for decisions, `SECURITY.md` for the threat posture.

- Frontend: SvelteKit 3, Svelte 5 runes, TypeScript, MapLibre GL 6, PMTiles, Playwright (unit, e2e, timing), pnpm 11.
- Backend: Python ≥ 3.11 with uv, pydantic (data contract), numpy, rasterio, pytest, ruff.
- Automation: GitHub Actions (CI, forecast archive), Cloudflare Worker `workers/archive-trigger/`.

@.claude/shared/workflow.md
