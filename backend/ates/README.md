# Draft terrain classes (AutoATES)

Draft Avalanche Terrain Exposure Scale classes for **Kožuf** and **Popova Šapka**, made to be reviewed with
guides, not published.

> **Draft, not an ATES map.** AutoATES v3.0 is calibrated for western Canada; here it runs on a 30 m surface
> model (Copernicus DEM, which includes tree canopy) and a forest proxy (ESA WorldCover). Nothing has been
> checked against local avalanche paths. The authors call such output "a research/tutorial product, not an
> operational ATES map". Do not show it in the public app until guides have reviewed it.

## Steps

1. **Inputs** (project environment, no extra installs):
   ```sh
   cd backend && uv run python ates/prepare_inputs.py          # -> backend/.cache/ates/<place>/
   ```
   `dem.tif` (UTM 34N, 30 m), `forest_canopy.tif` (tree cover 0–100 % per cell, from 10 m WorldCover) and
   `aoi.geojson` (the place's detail area plus 2 km, so avalanches starting above it are included).

2. **AutoATES** runs in its own conda-forge environment, because it needs GDAL's Python bindings. Its code
   (MIT) and AvaFrame (EUPL-1.2) stay outside this repository, in `backend/.cache/autoates/`:
   - [autoATES-v3.0-issw](https://github.com/AutoATES/autoATES-v3.0-issw) — the ISSW 2026 snapshot
   - [AvaFrame](https://github.com/OpenNHM/AvaFrame) at commit `c745a2dec4a7` (the version the workshop pins),
     with `python setup.py build_ext --inplace` for Flow-Py
   - Defaults are left unchanged (`autoATESCfg.ini`); only the three input paths are set per place.

   One-time setup, then the run:
   ```sh
   A=backend/.cache/autoates
   micromamba create -p $A/env -f backend/ates/autoates-environment.yml   # ISSW workshop env without notebooks
   git clone https://github.com/AutoATES/autoATES-v3.0-issw.git $A/src/autoATES-v3.0-issw   # commit 5558c16
   git clone https://github.com/OpenNHM/AvaFrame.git $A/src/AvaFrame && git -C $A/src/AvaFrame checkout c745a2dec4a7
   (cd $A/src/AvaFrame && ../../env/bin/python setup.py build_ext --inplace)
   backend/ates/run_autoates.sh                                # ~1 min per place; log in .cache/ates/<place>/
   ```

3. **Maps** (project environment):
   ```sh
   cd backend && uv run python ates/export_maps.py
   ```
   - `backend/.cache/ates/maps/<place>-draft-ates.pdf` (and `.png`): A4 landscape, 300 dpi, Macedonian and English,
     with a "НАЦРТ · DRAFT, not validated" banner and a two-language legend, for printing and marking up with guides.
   - `frontend/static/data/ates/`: overlay for the site, shown **only** with `?draft=ates` (Terrain tab → "ATES
     (draft)", with the draft warning). Normal visitors never see it (tested in `frontend/tests/e2e/draft.spec.ts`).

## First result (2026-11-15), for discussion

- Kožuf: simple 54 %, challenging 21 %, complex 7 % of the detail area; complex terrain on the steep faces south
  and east of the summit; the open bowl around the lifts mostly challenging.
- Popova Šapka: simple 37 %, challenging 39 %, complex 18 %, extreme 1 %; complex rises from 4 % at 1,200 m to
  57 % above 2,600 m (the Šar ridges west of the resort).
- Dense forest (over 80 % tree cover) comes out 72–86 % simple. Ask guides specifically about steep open gullies
  inside the forest: 30 m data and the forest map are weakest there.

## Settings kept at the authors' defaults, and why

- Ruggedness off: uncalibrated on ~30 m data.
- Typical (α 30°) and infrequent (α 18°) scenarios both kept.
- Class thresholds unchanged: the authors advise against tuning them without a local validation set.

## Credits

Elevation: Copernicus DEM GLO-30. Forest: © ESA WorldCover project 2021 / Contains modified Copernicus Sentinel
data (2021) processed by ESA WorldCover consortium (CC BY 4.0). Model: Sykes, J., Knies, D., Haegeli, P.,
Anthony-Malone, K., & Statham, G. (2026). AutoATES v3.0: Automated ATES mapping at scale across western Canada.
ISSW, Whistler.
