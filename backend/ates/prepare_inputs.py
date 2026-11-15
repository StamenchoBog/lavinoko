"""Prepare AutoATES inputs (elevation, forest canopy, area) for the draft terrain-class maps.

Usage:
    cd backend && uv run python ates/prepare_inputs.py [place ...]     # default: kozuf popova_sapka

Writes, per place, to backend/.cache/ates/<place>/ (not committed):
    dem.tif              Copernicus DEM GLO-30, UTM 34N, 30 m cells
    forest_canopy.tif    tree cover 0-100 % per 30 m cell, from ESA WorldCover 2021 (10 m)
    aoi.geojson          the area AutoATES classifies (the place's detail area plus a margin)

AutoATES itself (autoATES v3.0, MIT) runs separately in its own environment: see ates/README.md.
The result is a DRAFT for review by guides, not an ATES map: 30 m surface data and western-Canada
defaults, never validated here.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.transform import from_origin
from rasterio.warp import Resampling, reproject, transform_bounds
from rasterio.windows import from_bounds

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "terrain"))
from build_terrain import REGIONS, ROOT, build_mosaic  # noqa: E402

OUT = ROOT / "backend" / ".cache" / "ates"
UTM = CRS.from_epsg(32634)  # UTM zone 34N covers the whole country (18°E-24°E)
CELL_M = 30  # the resolution AutoATES v3.0 was calibrated on (~30 m surface model)
SUB = 3  # 10 m WorldCover cells per 30 m cell, per side
MARGIN_M = 2000  # terrain above the area: avalanches starting outside can run into it

WORLDCOVER_URL = (
    "https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/ESA_WorldCover_10m_2021_v200_{tile}_Map.tif"
)
WORLDCOVER_TREES = 10  # class "Tree cover"
WORLDCOVER_CREDIT = "© ESA WorldCover project 2021 / Contains modified Copernicus Sentinel data (2021) processed by ESA WorldCover consortium"


def utm_grid(bounds_lonlat, margin_m: float = MARGIN_M, cell: float = CELL_M):
    """A UTM grid with whole cells covering the lon/lat bounds plus a margin: (transform, width, height)."""
    w, s, e, n = transform_bounds("EPSG:4326", UTM, *bounds_lonlat, densify_pts=21)
    w, s = math.floor((w - margin_m) / cell) * cell, math.floor((s - margin_m) / cell) * cell
    e, n = math.ceil((e + margin_m) / cell) * cell, math.ceil((n + margin_m) / cell) * cell
    return from_origin(w, n, cell, cell), int((e - w) / cell), int((n - s) / cell)


def worldcover_tiles(bounds_lonlat) -> list[str]:
    """WorldCover 3°x3° tile names (south-west corner) covering the bounds, e.g. 'N39E021'."""
    w, s, e, n = bounds_lonlat
    lats = range(math.floor(s / 3) * 3, math.floor(n / 3) * 3 + 1, 3)
    lons = range(math.floor(w / 3) * 3, math.floor(e / 3) * 3 + 1, 3)
    return [f"N{la:02d}E{lo:03d}" for la in lats for lo in lons]


def block_mean_percent(trees: np.ndarray, sub: int = SUB) -> np.ndarray:
    """Share of tree cells in each sub x sub block, in percent (canopy cover proxy, 0-100)."""
    h, w = trees.shape[0] // sub, trees.shape[1] // sub
    blocks = trees[: h * sub, : w * sub].reshape(h, sub, w, sub)
    return (blocks.mean(axis=(1, 3)) * 100).astype("float32")


def lonlat_bounds_of(transform, width, height):
    """The grid's extent in lon/lat, for reading only the needed part of each source."""
    w, n = transform.c, transform.f
    e, s = w + width * transform.a, n + height * transform.e
    return transform_bounds(UTM, "EPSG:4326", w, s, e, n, densify_pts=21)


def write(path: Path, array: np.ndarray, transform, nodata) -> None:
    profile = {
        "driver": "GTiff",
        "height": array.shape[0],
        "width": array.shape[1],
        "count": 1,
        "dtype": array.dtype,
        "crs": UTM,
        "transform": transform,
        "nodata": nodata,
        "compress": "deflate",
    }
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(array, 1)


def build_dem(transform, width, height) -> np.ndarray:
    ll = lonlat_bounds_of(transform, width, height)
    pad = 0.01  # degrees, so bilinear sampling at the edge has neighbours
    mosaic = build_mosaic((ll[0] - pad, ll[1] - pad, ll[2] + pad, ll[3] + pad))
    dem = np.full((height, width), -9999, dtype="float32")
    with rasterio.open(mosaic) as src:
        reproject(
            rasterio.band(src, 1),
            dem,
            dst_transform=transform,
            dst_crs=UTM,
            dst_nodata=-9999,
            resampling=Resampling.bilinear,
        )
    if (dem == -9999).any():
        raise RuntimeError("DEM has gaps inside the area")
    return dem


def build_canopy(transform, width, height) -> np.ndarray:
    """Tree cover percent per 30 m cell, from 10 m WorldCover read remotely (only the needed window)."""
    fine_transform = transform * transform.scale(1 / SUB, 1 / SUB)
    trees = np.zeros((height * SUB, width * SUB), dtype="uint8")
    covered = np.zeros_like(trees, dtype=bool)
    ll = lonlat_bounds_of(transform, width, height)
    for tile in worldcover_tiles(ll):
        url = WORLDCOVER_URL.format(tile=tile)
        print(f"Reading {url}")
        with rasterio.open(url) as src:
            tb = src.bounds
            clip = (max(ll[0], tb.left), max(ll[1], tb.bottom), min(ll[2], tb.right), min(ll[3], tb.top))
            if clip[0] >= clip[2] or clip[1] >= clip[3]:
                continue
            win = from_bounds(*clip, transform=src.transform).round_offsets().round_lengths()
            classes = src.read(1, window=win, boundless=True, fill_value=0)
            src_transform = src.window_transform(win)
            part = np.zeros_like(trees)
            reproject(
                (classes == WORLDCOVER_TREES).astype("uint8") + 1,  # 1 = open, 2 = trees, 0 = no data
                part,
                src_transform=src_transform,
                src_crs=src.crs,
                dst_transform=fine_transform,
                dst_crs=UTM,
                src_nodata=0,
                dst_nodata=0,
                resampling=Resampling.nearest,
            )
            got = part > 0
            trees[got] = part[got] - 1
            covered |= got
    if not covered.all():
        raise RuntimeError(f"WorldCover does not cover the whole area ({(~covered).mean():.1%} missing)")
    return block_mean_percent(trees)


def aoi_geojson(transform, width, height) -> dict:
    w, n = transform.c, transform.f
    e, s = w + width * transform.a, n + height * transform.e
    ring = [[w, s], [e, s], [e, n], [w, n], [w, s]]
    return {
        "type": "FeatureCollection",
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:EPSG::32634"}},
        "features": [{"type": "Feature", "properties": {}, "geometry": {"type": "Polygon", "coordinates": [ring]}}],
    }


def prepare(place_id: str) -> Path:
    place = next((p for p in REGIONS["places"] if p["id"] == place_id), None)
    if place is None:
        raise SystemExit(f"Unknown place: {place_id}")
    transform, width, height = utm_grid(place["detail_bounds"])
    out = OUT / place_id
    out.mkdir(parents=True, exist_ok=True)
    print(f"{place_id}: {width} x {height} cells of {CELL_M} m")
    write(out / "dem.tif", build_dem(transform, width, height), transform, -9999)
    canopy = build_canopy(transform, width, height)
    write(out / "forest_canopy.tif", canopy, transform, -1)
    (out / "aoi.geojson").write_text(json.dumps(aoi_geojson(transform, width, height)))
    (out / "sources.txt").write_text(
        "Elevation: Copernicus DEM GLO-30. Forest: " + WORLDCOVER_CREDIT + " (CC BY 4.0).\n"
    )
    print(f"  forest: {np.mean(canopy > 50):.0%} of cells over 50 % tree cover -> {out}")
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("places", nargs="*", default=["kozuf", "popova_sapka"])
    for pid in ap.parse_args().places:
        prepare(pid)


if __name__ == "__main__":
    main()
