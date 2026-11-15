#!/usr/bin/env bash
# Run AutoATES v3.0 on the prepared areas (see ates/README.md).
#
#   backend/ates/run_autoates.sh [place ...]        # default: kozuf popova_sapka
#
# Needs, under backend/.cache/autoates/ (not committed):
#   env/                          conda-forge environment (environment.yml there; micromamba create -p env -f ...)
#   src/autoATES-v3.0-issw/       AutoATES v3.0 ISSW snapshot, commit 5558c16
#   src/AvaFrame/                 AvaFrame at commit c745a2dec4a7, built once with
#                                 env/bin/python setup.py build_ext --inplace
# and the inputs from: cd backend && uv run python ates/prepare_inputs.py
#
# Settings are the authors' defaults (autoATESCfg.ini); only the input and output paths change.
set -euo pipefail

BACKEND="$(cd "$(dirname "$0")/.." && pwd)"
AA="$BACKEND/.cache/autoates"
PY="$AA/env/bin/python"
SRC="$AA/src/autoATES-v3.0-issw"
export PYTHONPATH="$SRC:$AA/src/AvaFrame${PYTHONPATH:+:$PYTHONPATH}"

[ -x "$PY" ] || { echo "Missing $PY (create the environment first)"; exit 1; }
ls "$AA"/src/AvaFrame/avaframe/com1DFA/DFAfunctionsCython*.so >/dev/null 2>&1 \
  || { echo "AvaFrame is not built: cd $AA/src/AvaFrame && $PY setup.py build_ext --inplace"; exit 1; }

places=("$@")
[ ${#places[@]} -gt 0 ] || places=(kozuf popova_sapka)

for place in "${places[@]}"; do
  dir="$BACKEND/.cache/ates/$place"
  [ -f "$dir/dem.tif" ] || { echo "No inputs for $place: run ates/prepare_inputs.py"; exit 1; }
  # Copy the default settings and set only the paths (stdlib configparser, keeps every other key).
  "$PY" - "$SRC/autoates/comAutoATES/autoATESCfg.ini" "$dir" "$place" <<'EOF'
import configparser, sys
default, d, place = sys.argv[1:]
c = configparser.ConfigParser()
c.optionxform = str  # keep key case
c.read(default)
c["General"]["project_name"] = place
c["General"]["working_dir"] = f"{d}/outputs"
c["General"]["output_basename"] = place
c["General"]["aoi_path"] = f"{d}/aoi.geojson"
c["Input"]["dem_path"] = f"{d}/dem.tif"
c["Input"]["forest_canopy_path"] = f"{d}/forest_canopy.tif"
with open(f"{d}/autoates.ini", "w") as f:
    c.write(f)
EOF
  echo "== $place"
  (cd "$dir" && "$PY" "$SRC/run_autoates.py" "$dir/autoates.ini" 2>&1 | tee "$dir/autoates.log" | tail -5)
done
