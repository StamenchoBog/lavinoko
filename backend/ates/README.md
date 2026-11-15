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

## Settings kept at the authors' defaults, and why

- Ruggedness off: uncalibrated on ~30 m data.
- Typical (α 30°) and infrequent (α 18°) scenarios both kept.
- Class thresholds unchanged: the authors advise against tuning them without a local validation set.

## Credits

Elevation: Copernicus DEM GLO-30. Forest: © ESA WorldCover project 2021 / Contains modified Copernicus Sentinel
data (2021) processed by ESA WorldCover consortium (CC BY 4.0). Model: Sykes, J., Knies, D., Haegeli, P.,
Anthony-Malone, K., & Statham, G. (2026). AutoATES v3.0: Automated ATES mapping at scale across western Canada.
ISSW, Whistler.
