"""Build our own base map for North Macedonia and the border ranges, so the site needs no external map service.

Usage:
    cd backend && uv run --with osmium python basemap/build_basemap.py            # reuse downloaded data
    cd backend && uv run --with osmium python basemap/build_basemap.py --refresh  # fresh OpenStreetMap data

Refresh before each winter (new trails, huts, lifts get mapped); terrain and weather don't depend on it.

Steps:
  1. Download OpenStreetMap extracts (Geofabrik) for North Macedonia and its neighbours, because the
     ranges we cover (Šar, Korab, Kožuf, Nidže) straddle the border. Merge them into one file.
  2. Run Planetiler (OpenMapTiles schema, the same as OpenFreeMap) clipped to our area -> basemap.pmtiles.
  3. Copy the map style (OpenFreeMap "Liberty"), its fonts and sprites, pointing everything at local files.

Output: frontend/static/data/basemap/ (not committed; rebuild with this script). Needs Java 21+.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from urllib.request import Request, urlopen

import osmium

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / "backend" / ".cache" / "basemap"
OUT = ROOT / "frontend" / "static" / "data" / "basemap"
REGIONS = json.loads((ROOT / "config" / "regions.json").read_text())

PLANETILER = "https://github.com/onthegomap/planetiler/releases/download/v0.10.2/planetiler.jar"
EXTRACTS = ["macedonia", "albania", "kosovo", "greece"]
STYLE_URL = "https://tiles.openfreemap.org/styles/liberty"
UA = {"User-Agent": "lavinoko/0.1 (+https://github.com/StamenchoBog/lavinoko)"}

FONTS = ["Noto Sans Regular", "Noto Sans Bold", "Noto Sans Italic"]
# Unicode blocks of 256 code points: Latin and Latin Extended (A, B and Additional: ẞ, ṭ, ẓ in
# transliterated names), Greek, Cyrillic, punctuation, arrows/symbols (⌂ ▲). A missing block is a
# 404 in the browser and unlabelled names on the map.
GLYPH_RANGES = [0, 256, 512, 768, 1024, 1280, 7680, 8192, 8448, 8704, 8960, 9472, 9728]


def download(url: str, path: Path) -> Path:
    if path.exists():
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {url}")
    tmp = path.with_suffix(path.suffix + ".part")
    with urlopen(Request(url, headers=UA), timeout=600) as r, open(tmp, "wb") as f:
        while chunk := r.read(1 << 20):
            f.write(chunk)
    tmp.rename(path)
    return path


def bounds_with_margin(margin: float = 0.25) -> list[float]:
    w, s, e, n = REGIONS["country"]["bounds"]
    return [w - margin, s - margin, e + margin, n + margin]


def merged_osm() -> Path:
    merged = CACHE / "merged.osm.pbf"
    if merged.exists():
        return merged
    files = [
        download(f"https://download.geofabrik.de/europe/{a}-latest.osm.pbf", CACHE / f"{a}.osm.pbf") for a in EXTRACTS
    ]
    print("Merging extracts")
    reader = osmium.MergeInputReader()
    for f in files:
        reader.add_file(str(f))
    writer = osmium.SimpleWriter(str(merged))
    reader.apply(writer, simplify=True)
    writer.close()
    return merged


def build_tiles(osm: Path) -> None:
    jar = download(PLANETILER, CACHE / "planetiler.jar")
    OUT.mkdir(parents=True, exist_ok=True)
    w, s, e, n = bounds_with_margin()
    subprocess.run(
        [
            "java",
            "-Xmx3g",
            "-jar",
            str(jar),
            f"--osm-path={osm}",
            "--download",
            f"--download-dir={CACHE / 'sources'}",
            f"--tmpdir={CACHE / 'tmp'}",
            f"--bounds={w},{s},{e},{n}",
            f"--output={OUT / 'basemap.pmtiles'}",
            "--force",
            # Buildings and house numbers are hidden on our map anyway; leaving them out shrinks the file.
            "--exclude_layers=building,housenumber",
        ],
        check=True,
    )


def build_style() -> None:
    style = json.loads(urlopen(Request(STYLE_URL, headers=UA), timeout=60).read())
    # Fonts and sprites, stored next to the style.
    for font in FONTS:
        for start in GLYPH_RANGES:
            rng = f"{start}-{start + 255}"
            url = style["glyphs"].replace("{fontstack}", font.replace(" ", "%20")).replace("{range}", rng)
            download(url, OUT / "fonts" / font / f"{rng}.pbf")
    sprite = style["sprite"] if isinstance(style["sprite"], str) else style["sprite"][0]["url"]
    for suffix in (".json", ".png", "@2x.json", "@2x.png"):
        download(sprite + suffix, OUT / "sprites" / f"liberty{suffix}")

    # Point the style at local files. Paths are relative to the site; the page makes them absolute.
    style["sources"] = {
        "openmaptiles": {
            "type": "vector",
            "url": "pmtiles://{base}/data/basemap/basemap.pmtiles",
            "attribution": "© OpenMapTiles © OpenStreetMap contributors",
        }
    }
    style["glyphs"] = "{base}/data/basemap/fonts/{fontstack}/{range}.pbf"
    style["sprite"] = "{base}/data/basemap/sprites/liberty"
    # The world-wide shaded relief raster is replaced by our own relief layer.
    style["layers"] = [layer for layer in style["layers"] if layer.get("source") in (None, "openmaptiles")]
    (OUT / "style.json").write_text(json.dumps(style, ensure_ascii=False, separators=(",", ":")))


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the base map for North Macedonia and border ranges.")
    parser.add_argument("--refresh", action="store_true", help="download fresh OpenStreetMap extracts first")
    if parser.parse_args().refresh:
        for f in [CACHE / "merged.osm.pbf", *(CACHE / f"{a}.osm.pbf" for a in EXTRACTS)]:
            f.unlink(missing_ok=True)
    build_tiles(merged_osm())
    build_style()
    size = (OUT / "basemap.pmtiles").stat().st_size / 1e6
    print(f"Base map: {size:.1f} MB. Wrote {OUT}")


if __name__ == "__main__":
    main()
