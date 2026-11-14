"""Build slope, aspect and relief layers for the whole country from the Copernicus DEM.

Usage:
    cd backend && uv run python terrain/build_terrain.py

Two sets of PMTiles archives go to frontend/static/data/terrain/:

    <layer>.pmtiles          whole country (and border ranges), zoom 8-13
    <layer>-detail.pmtiles   ski areas and other detail zones only, zoom 14-15

Zoom 13 is ~15 m per screen pixel here, already finer than the 30 m source; beyond it the
country layer is simply enlarged by the map. Detail zones get their own zoom 14-15 tiles; this
is where better elevation data (national DEM, drone surveys) will be plugged in later.

The country is processed in chunks (one map tile at a time) so memory stays small. For zoom
10-15 the DEM is resampled from 30 m to 10 m (cubic) before slopes are computed. This gives
smoother, more legible slope bands; it does not add real detail.
"""

from __future__ import annotations

import argparse
import io
import json
import math
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlretrieve

import numpy as np
import rasterio
from PIL import Image
from pmtiles.tile import Compression, TileType, zxy_to_tileid
from pmtiles.writer import write as pmtiles_write
from rasterio.enums import Resampling
from rasterio.merge import merge
from rasterio.windows import from_bounds

ROOT = Path(__file__).resolve().parents[2]  # repository root
CACHE = ROOT / "backend" / ".cache" / "dem"  # downloaded DEM tiles (not committed)
OUT = ROOT / "frontend" / "static" / "data" / "terrain"
REGIONS = json.loads((ROOT / "config" / "regions.json").read_text())

DEM_URL = (
    "https://copernicus-dem-30m.s3.amazonaws.com/Copernicus_DSM_COG_10_{tile}_DEM/Copernicus_DSM_COG_10_{tile}_DEM.tif"
)
# Exact notice required for modified Copernicus DEM data (see config/sources.json).
ATTRIBUTION = (
    "Produced using Copernicus WorldDEM-30 © DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018 "
    "provided under COPERNICUS by the European Union and ESA; all rights reserved"
)

# Slope classes used on avalanche terrain maps (degrees, RGBA).
# Below 30° slab avalanches rarely release; 30-45° is the main release range.
SLOPE_CLASSES = [
    (27, 30, (180, 230, 120, 150)),
    (30, 35, (250, 220, 40, 190)),
    (35, 40, (245, 140, 30, 200)),
    (40, 45, (220, 40, 40, 210)),
    (45, 90, (140, 60, 170, 220)),
]

# Aspect colours by compass sector (N, NE, E, SE, S, SW, W, NW).
ASPECT_COLOURS = [
    (40, 70, 200),
    (60, 160, 220),
    (90, 190, 120),
    (220, 200, 60),
    (230, 120, 40),
    (210, 60, 60),
    (170, 70, 170),
    (90, 70, 190),
]
ASPECT_NAMES = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
ASPECT_ALPHA = 190

TILE_SIZE = 256
SOURCE_RES_DEG = 1 / 3600  # Copernicus GLO-30 at this latitude: 1 arc-second

# (chunk zoom, output zooms, resampling factor vs the 30 m source)
COUNTRY_LEVELS = [(7, range(8, 10), 0.5), (10, range(10, 14), 3)]
DETAIL_LEVELS = [(12, range(14, 16), 3)]
# Relief shading is continuous (not a few flat colours), so its tiles are much larger. Over the
# whole country it stops one zoom earlier; detail zones still get full-resolution shading.
COUNTRY_RELIEF_MAX_ZOOM = 12

# Contour lines (minor, major interval in metres) per zoom; none below 12, where they would be too dense.
CONTOUR_INTERVALS = {12: (100, 500), 13: (50, 250), 14: (20, 100), 15: (20, 100)}
CONTOUR_COLOURS = [(120, 80, 45, 70), (105, 65, 30, 150)]  # minor, major (topographic brown)


def tile_name(lat: int, lon: int) -> str:
    ns = "N" if lat >= 0 else "S"
    ew = "E" if lon >= 0 else "W"
    return f"{ns}{abs(lat):02d}_00_{ew}{abs(lon):03d}_00"


def fetch_tile(lat: int, lon: int) -> Path | None:
    """Download one 1°x1° DEM tile (cached). None where no tile exists (open sea)."""
    name = tile_name(lat, lon)
    path = CACHE / f"copdem30_{name}.tif"
    if not path.exists():
        CACHE.mkdir(parents=True, exist_ok=True)
        url = DEM_URL.format(tile=name)
        print(f"Downloading {url}")
        try:
            urlretrieve(url, path)
        except HTTPError as e:
            if e.code in (403, 404):
                return None
            raise
    return path


def snap_to_dem_grid(bounds) -> tuple[float, float, float, float]:
    """Expand bounds onto the DEM's own pixel grid (edges at whole degrees minus half a pixel).

    Merging onto an offset grid makes rows on a tile boundary ambiguous: one gets skipped and
    shows up as a straight line across the slope map.
    """
    r = SOURCE_RES_DEG
    lo = lambda v: (math.floor(v / r + 0.5) - 0.5) * r  # noqa: E731
    hi = lambda v: (math.ceil(v / r + 0.5) - 0.5) * r  # noqa: E731
    west, south, east, north = bounds
    return lo(west), lo(south), hi(east), hi(north)


def build_mosaic(bounds) -> Path:
    """Join the DEM tiles covering the bounds into one cached GeoTIFF."""
    bounds = snap_to_dem_grid(bounds)
    west, south, east, north = bounds
    out = CACHE / f"mosaic_{west:.5f}_{south:.5f}_{east:.5f}_{north:.5f}.tif"
    if out.exists():
        return out
    paths = [
        p
        for lat in range(math.floor(south), math.floor(north - 1e-9) + 1)
        for lon in range(math.floor(west), math.floor(east - 1e-9) + 1)
        if (p := fetch_tile(lat, lon)) is not None
    ]
    sources = [rasterio.open(p) for p in paths]
    try:
        array, transform = merge(sources, bounds=bounds, nodata=-9999)
        profile = sources[0].profile | {
            "height": array.shape[1],
            "width": array.shape[2],
            "transform": transform,
            "count": 1,
            "nodata": -9999,
            "compress": "deflate",
            "tiled": True,
            "dtype": "float32",
        }
    finally:
        for s in sources:
            s.close()
    with rasterio.open(out, "w", **profile) as dst:
        dst.write(array.astype("float32"))
    return out


def read_window(src, bounds, factor: float) -> tuple[np.ndarray, object]:
    """Read a lon/lat window, resampled by `factor` (3 = 10 m, 0.5 = 60 m). Nodata becomes NaN."""
    window = from_bounds(*bounds, src.transform).round_offsets().round_lengths()
    h, w = max(1, int(window.height * factor)), max(1, int(window.width * factor))
    resampling = Resampling.cubic if factor > 1 else Resampling.average
    dem = src.read(1, window=window, out_shape=(h, w), resampling=resampling, boundless=True, fill_value=-9999)
    dem = dem.astype("float64")
    dem[dem <= -9000] = np.nan
    base = src.window_transform(window)
    return dem, base * base.scale(window.width / w, window.height / h)


def slope_aspect(dem: np.ndarray, transform, mean_lat: float) -> tuple[np.ndarray, np.ndarray]:
    """Slope (degrees) and aspect (degrees clockwise from north, direction the slope faces)."""
    m_per_deg_lat = 111_320.0
    dx = abs(transform.a) * m_per_deg_lat * math.cos(math.radians(mean_lat))
    dy = abs(transform.e) * m_per_deg_lat
    # Rows go north -> south, columns west -> east.
    dz_dy_rows, dz_dx = np.gradient(dem, dy, dx)
    dz_dnorth = -dz_dy_rows
    slope = np.degrees(np.arctan(np.hypot(dz_dx, dz_dnorth)))
    # Downhill direction is the negative gradient.
    aspect = (np.degrees(np.arctan2(-dz_dx, -dz_dnorth)) + 360.0) % 360.0
    return slope, aspect


def hillshade(slope: np.ndarray, aspect: np.ndarray, azimuth=315.0, altitude=45.0) -> np.ndarray:
    """Illumination 0 (dark) .. 1 (lit), light from the north-west."""
    s, a = np.radians(slope), np.radians(aspect)
    az, alt = np.radians(azimuth), np.radians(altitude)
    return np.clip(np.sin(alt) * np.cos(s) + np.cos(alt) * np.sin(s) * np.cos(az - a), 0, 1)


def aspect_sector(aspect: np.ndarray) -> np.ndarray:
    return (((aspect + 22.5) % 360) // 45).astype(int)


def slope_index(slope: np.ndarray) -> np.ndarray:
    """0 = transparent, 1..n = slope class."""
    idx = np.zeros(slope.shape, dtype=np.uint8)
    for i, (lo, hi, _) in enumerate(SLOPE_CLASSES, start=1):
        idx[(slope >= lo) & (slope < hi)] = i
    return idx


def aspect_index(slope: np.ndarray, aspect: np.ndarray, min_slope: float = 25.0) -> np.ndarray:
    """0 = transparent (gentle terrain), 1..8 = N, NE, ... NW."""
    idx = (aspect_sector(np.nan_to_num(aspect)) + 1).astype(np.uint8)
    idx[~(slope >= min_slope)] = 0  # also clears NaN
    return idx


def shadow_alpha(shade: np.ndarray, altitude=45.0) -> np.ndarray:
    """Shadows only: flat ground stays fully transparent, slopes facing away from the light darken."""
    flat = math.sin(math.radians(altitude))
    shade = np.nan_to_num(shade, nan=flat)
    a = np.clip((flat - shade) / flat, 0, 1) * 210
    return a.astype(np.uint8)


def tile_range(bounds, z: int) -> tuple[range, range]:
    """Tile x and y ranges covering the bounds."""
    west, south, east, north = bounds
    n = 2**z

    def tx(lon):
        return min(n - 1, int((lon + 180) / 360 * n))

    def ty(lat):
        return min(n - 1, int((1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n))

    return range(tx(west), tx(east) + 1), range(ty(north), ty(south) + 1)


def tile_bounds(z: int, x: int, y: int) -> tuple[float, float, float, float]:
    n = 2**z

    def lat(yy):
        return math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * yy / n))))

    return x / n * 360 - 180, lat(y + 1), (x + 1) / n * 360 - 180, lat(y)


def tile_pixel_lonlat(z: int, x: int, y: int) -> tuple[np.ndarray, np.ndarray]:
    """Longitudes of the pixel columns and latitudes of the pixel rows of one tile."""
    n = 2**z
    f = (np.arange(TILE_SIZE) + 0.5) / TILE_SIZE
    lon = (x + f) / n * 360 - 180
    lat = np.degrees(np.arctan(np.sinh(np.pi * (1 - 2 * (y + f) / n))))
    return lon, lat


def sample_tile(values: np.ndarray, transform, z: int, x: int, y: int) -> np.ndarray:
    """Nearest-neighbour sample of a lon/lat grid onto one tile (0 outside the grid)."""
    rows_n, cols_n = values.shape
    lon, lat = tile_pixel_lonlat(z, x, y)
    col = np.floor((lon - transform.c) / transform.a).astype(int)
    row = np.floor((lat - transform.f) / transform.e).astype(int)
    ok_c = (col >= 0) & (col < cols_n)
    ok_r = (row >= 0) & (row < rows_n)
    tile = np.zeros((TILE_SIZE, TILE_SIZE), dtype=values.dtype)
    tile[np.ix_(ok_r, ok_c)] = values[np.ix_(row[ok_r], col[ok_c])]
    return tile


def sample_tile_bilinear(values: np.ndarray, transform, z: int, x: int, y: int) -> np.ndarray:
    """Smooth (bilinear) sample of a lon/lat grid onto one tile; NaN outside the grid."""
    rows_n, cols_n = values.shape
    lon, lat = tile_pixel_lonlat(z, x, y)
    c = (lon - transform.c) / transform.a - 0.5
    r = (lat - transform.f) / transform.e - 0.5
    c0 = np.clip(np.floor(c).astype(int), 0, cols_n - 2)
    r0 = np.clip(np.floor(r).astype(int), 0, rows_n - 2)
    fc = np.clip(c - c0, 0, 1)[None, :]
    fr = np.clip(r - r0, 0, 1)[:, None]
    v00 = values[np.ix_(r0, c0)]
    v01 = values[np.ix_(r0, c0 + 1)]
    v10 = values[np.ix_(r0 + 1, c0)]
    v11 = values[np.ix_(r0 + 1, c0 + 1)]
    out = (v00 * (1 - fc) + v01 * fc) * (1 - fr) + (v10 * (1 - fc) + v11 * fc) * fr
    inside = ((c >= -0.5) & (c <= cols_n - 0.5))[None, :] & ((r >= -0.5) & (r <= rows_n - 0.5))[:, None]
    return np.where(inside, out, np.nan)


def contour_index(elev: np.ndarray, minor: float, major: float) -> np.ndarray:
    """0 = none, 1 = minor contour, 2 = major contour: pixels where elevation crosses a level."""
    valid = ~np.isnan(elev)
    e = np.nan_to_num(elev)

    def crossings(interval: float) -> np.ndarray:
        level = np.floor(e / interval)
        edge = np.zeros(e.shape, dtype=bool)
        edge[:, 1:] |= level[:, 1:] != level[:, :-1]
        edge[1:, :] |= level[1:, :] != level[:-1, :]
        both = valid.copy()
        both[:, 1:] &= valid[:, :-1]
        both[1:, :] &= valid[:-1, :]
        return edge & both

    idx = np.zeros(e.shape, dtype=np.uint8)
    idx[crossings(minor)] = 1
    major_px = crossings(major)
    major_px[:, 1:] |= major_px[:, :-1]  # major lines one pixel wider
    idx[major_px] = 2
    return idx


def intersects(a, b) -> bool:
    return a[0] < b[2] and a[2] > b[0] and a[1] < b[3] and a[3] > b[1]


def _palette(colours: list[tuple]) -> tuple[list[int], bytes]:
    rgb, alpha = [0, 0, 0], [0]
    for c in colours:
        rgb += list(c[:3])
        alpha.append(c[3])
    return rgb, bytes(alpha)


SLOPE_PALETTE = _palette([c for _, _, c in SLOPE_CLASSES])
CONTOUR_PALETTE = _palette(CONTOUR_COLOURS)
ASPECT_PALETTE = _palette([(*c, ASPECT_ALPHA) for c in ASPECT_COLOURS])


def encode_class_png(index_tile: np.ndarray, palette: tuple[list[int], bytes]) -> bytes:
    img = Image.fromarray(index_tile, "P")
    img.putpalette(palette[0])
    buf = io.BytesIO()
    img.save(buf, "PNG", optimize=True, transparency=palette[1])
    return buf.getvalue()


def encode_shade_webp(alpha_tile: np.ndarray) -> bytes:
    rgba = np.zeros((TILE_SIZE, TILE_SIZE, 4), dtype=np.uint8)
    rgba[..., :3] = (43, 58, 74)  # slate shadow
    rgba[..., 3] = alpha_tile
    buf = io.BytesIO()
    Image.fromarray(rgba, "RGBA").save(buf, "WEBP", quality=65, method=4)  # method 6 is ~500x slower
    return buf.getvalue()


def write_pmtiles(path: Path, tiles: dict[int, bytes], tile_type, zooms: tuple[int, int], bounds, center) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    west, south, east, north = bounds
    e7 = lambda v: int(round(v * 1e7))  # noqa: E731
    with pmtiles_write(str(path)) as w:
        for tid in sorted(tiles):  # clustered archives need ascending tile ids
            w.write_tile(tid, tiles[tid])
        w.finalize(
            {
                "tile_type": tile_type,
                "tile_compression": Compression.NONE,  # PNG/WebP are already compressed
                "min_zoom": zooms[0],
                "max_zoom": zooms[1],
                "min_lon_e7": e7(west),
                "min_lat_e7": e7(south),
                "max_lon_e7": e7(east),
                "max_lat_e7": e7(north),
                "center_zoom": zooms[0] + 1,
                "center_lon_e7": e7(center[0]),
                "center_lat_e7": e7(center[1]),
            },
            {"attribution": ATTRIBUTION},
        )


def render(src, zones: list, levels: list, relief_max_zoom: int = 99) -> dict[str, dict[int, bytes]]:
    """Render slope/aspect/relief/contour tiles for every tile that touches one of the zones."""
    out: dict[str, dict[int, bytes]] = {"slope": {}, "aspect": {}, "relief": {}, "contours": {}}
    for chunk_z, zooms, factor in levels:
        chunks = sorted(
            {(x, y) for zone in zones for x in tile_range(zone, chunk_z)[0] for y in tile_range(zone, chunk_z)[1]}
        )
        for i, (cx, cy) in enumerate(chunks, 1):
            cb = tile_bounds(chunk_z, cx, cy)
            if not any(intersects(cb, zone) for zone in zones):
                continue
            # A margin of a few source pixels so slopes at the chunk edge are computed correctly.
            m = 4 * SOURCE_RES_DEG
            dem, transform = read_window(src, (cb[0] - m, cb[1] - m, cb[2] + m, cb[3] + m), factor)
            if np.isnan(dem).all():
                continue
            slope, aspect = slope_aspect(dem, transform, (cb[1] + cb[3]) / 2)
            s_idx, a_idx, shade = (
                slope_index(slope),
                aspect_index(slope, aspect),
                shadow_alpha(hillshade(slope, aspect)),
            )
            for z in zooms:
                k = 2 ** (z - chunk_z)
                for x in range(cx * k, (cx + 1) * k):
                    for y in range(cy * k, (cy + 1) * k):
                        if not any(intersects(tile_bounds(z, x, y), zone) for zone in zones):
                            continue
                        tid = zxy_to_tileid(z, x, y)
                        t = sample_tile(s_idx, transform, z, x, y)
                        if t.any():
                            out["slope"][tid] = encode_class_png(t, SLOPE_PALETTE)
                        t = sample_tile(a_idx, transform, z, x, y)
                        if t.any():
                            out["aspect"][tid] = encode_class_png(t, ASPECT_PALETTE)
                        if z in CONTOUR_INTERVALS:
                            elev = sample_tile_bilinear(dem, transform, z, x, y)
                            t = contour_index(elev, *CONTOUR_INTERVALS[z])
                            if t.any():
                                out["contours"][tid] = encode_class_png(t, CONTOUR_PALETTE)
                        if z > relief_max_zoom:
                            continue
                        t = sample_tile(shade, transform, z, x, y)
                        if t.any():
                            out["relief"][tid] = encode_shade_webp(t)
            print(f"  zoom {zooms.start}-{zooms.stop - 1}: chunk {i}/{len(chunks)}", end="\r")
        print()
    return out


def detail_zones() -> list[tuple[float, float, float, float]]:
    return [tuple(p["detail_bounds"]) for p in REGIONS["places"] if p.get("detail_bounds")]


def build() -> dict:
    country = REGIONS["country"]
    bounds = tuple(country["bounds"])
    center = country["center"]
    mosaic = build_mosaic(bounds)
    OUT.mkdir(parents=True, exist_ok=True)
    counts = {}
    with rasterio.open(mosaic) as src:
        print("Country layers")
        country_tiles = render(src, [bounds], COUNTRY_LEVELS, COUNTRY_RELIEF_MAX_ZOOM)
        zones = detail_zones()
        print(f"Detail layers ({len(zones)} zones)")
        detail_tiles = render(src, zones, DETAIL_LEVELS) if zones else {k: {} for k in country_tiles}
        dem = src.read(1, out_shape=(src.height // 4, src.width // 4), resampling=Resampling.average)
        dem = dem[dem > -9000]

    layers = (
        ("slope", TileType.PNG),
        ("aspect", TileType.PNG),
        ("relief", TileType.WEBP),
        ("contours", TileType.PNG),
    )
    for name, ttype in layers:
        low = min(CONTOUR_INTERVALS) if name == "contours" else 8
        top = COUNTRY_RELIEF_MAX_ZOOM if name == "relief" else 13
        write_pmtiles(OUT / f"{name}.pmtiles", country_tiles[name], ttype, (low, top), bounds, center)
        write_pmtiles(OUT / f"{name}-detail.pmtiles", detail_tiles[name], ttype, (14, 15), bounds, center)
        counts[name] = (len(country_tiles[name]), len(detail_tiles[name]))

    meta = {
        "bounds": list(bounds),
        "center": center,
        "layers": {
            n: {"country": f"{n}.pmtiles", "detail": f"{n}-detail.pmtiles"}
            for n in ("slope", "aspect", "relief", "contours")
        },
        "country_zooms": [8, 13],
        "detail_zooms": [14, 15],
        "resolution_m": 10,
        "source": ATTRIBUTION,
        "slope_legend": [
            {"label": f"{lo}–{hi}°" if hi < 90 else f"≥{lo}°", "rgba": list(c)} for lo, hi, c in SLOPE_CLASSES
        ],
        "aspect_legend": [{"label": n, "rgb": list(c)} for n, c in zip(ASPECT_NAMES, ASPECT_COLOURS, strict=True)],
        "stats": {"elevation_min_m": round(float(dem.min())), "elevation_max_m": round(float(dem.max()))},
    }
    (OUT / "metadata.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2))
    for name, (c, d) in counts.items():
        size = sum((OUT / f).stat().st_size for f in (f"{name}.pmtiles", f"{name}-detail.pmtiles")) / 1e6
        print(f"{name}: {c} country tiles, {d} detail tiles, {size:.1f} MB")
    return meta


def main() -> None:
    argparse.ArgumentParser(description="Build country-wide avalanche terrain layers.").parse_args()
    meta = build()
    s = meta["stats"]
    print(f"Elevation {s['elevation_min_m']}–{s['elevation_max_m']} m. Wrote {OUT}")


if __name__ == "__main__":
    main()
