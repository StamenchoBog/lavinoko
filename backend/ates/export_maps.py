"""Turn AutoATES results into draft maps for review with guides.

Usage:
    cd backend && uv run python ates/export_maps.py [place ...]     # default: kozuf popova_sapka

Reads backend/.cache/ates/<place>/outputs/ATES/ATES_classification.tif (see ates/run_autoates.sh) and writes:
    backend/.cache/ates/maps/<place>-draft-ates.pdf / .png   A4 landscape print, Macedonian and English
    frontend/static/data/ates/<place>.png + index.json        overlay for the hidden draft layer (?draft=ates)

Every output says DRAFT: not validated, not for decisions in the field.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

import numpy as np
import rasterio
from PIL import Image, ImageDraw, ImageFont
from rasterio.warp import Resampling, calculate_default_transform, reproject, transform_bounds
from rasterio.warp import transform as warp_points
from rasterio.windows import from_bounds

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "terrain"))
from build_terrain import REGIONS, ROOT  # noqa: E402

CACHE = ROOT / "backend" / ".cache" / "ates"
WEB = ROOT / "frontend" / "static" / "data" / "ates"

# AutoATES v3.0 palette (autoates/comAutoATES/out1/palettes/ates_class.txt): colour-blind friendly,
# non-avalanche terrain transparent.
CLASSES = {
    0: {"rgb": None, "mk": "Без лавински терен", "en": "Non-avalanche terrain"},
    1: {"rgb": (144, 239, 152), "mk": "Едноставен", "en": "Simple"},
    2: {"rgb": (0, 173, 255), "mk": "Предизвикувачки", "en": "Challenging"},
    3: {"rgb": (241, 83, 147), "mk": "Сложен", "en": "Complex"},
    4: {"rgb": (180, 0, 255), "mk": "Екстремен", "en": "Extreme"},
}
WEB_ALPHA = 166  # as in the AutoATES palette (~65 %)

A4 = (3508, 2480)  # landscape, 300 dpi
DPI = 300
FONT = "/System/Library/Fonts/Supplemental/Arial.ttf"
FONT_BOLD = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"


def font(size: int, bold: bool = False):
    try:
        return ImageFont.truetype(FONT_BOLD if bold else FONT, size)
    except OSError:  # not macOS: Pillow's own font (Latin only)
        return ImageFont.load_default(size)


def colourise(cls: np.ndarray, alpha: int = 255) -> np.ndarray:
    """RGBA image of the classes; non-avalanche and no-data stay transparent."""
    out = np.zeros((*cls.shape, 4), dtype="uint8")
    for k, c in CLASSES.items():
        if c["rgb"]:
            out[cls == k] = (*c["rgb"], alpha)
    return out


def hillshade(dem: np.ndarray, cell: float, azimuth: float = 315, altitude: float = 45) -> np.ndarray:
    """0-1 shading, light from the north-west."""
    gy, gx = np.gradient(dem, cell)
    slope = np.arctan(np.hypot(gx, gy))
    aspect = np.arctan2(-gx, gy)
    az, alt = np.radians(360 - azimuth + 90), np.radians(altitude)
    shade = np.sin(alt) * np.cos(slope) + np.cos(alt) * np.sin(slope) * np.cos(az - aspect)
    return np.clip(shade, 0, 1)


def read_detail(path: Path, bounds_lonlat):
    with rasterio.open(path) as src:
        b = transform_bounds("EPSG:4326", src.crs, *bounds_lonlat, densify_pts=21)
        win = from_bounds(*b, transform=src.transform).round_offsets().round_lengths()
        return src.read(1, window=win), src.window_transform(win), src.crs


def web_overlay(place: dict, cls_path: Path) -> dict:
    """Reproject the classes to Web Mercator so the image's corners are a lon/lat rectangle for MapLibre."""
    with rasterio.open(cls_path) as src:
        transform, w, h = calculate_default_transform(
            src.crs, "EPSG:3857", src.width, src.height, *src.bounds, resolution=20
        )
        dst = np.full((h, w), -9999, dtype="int16")
        reproject(
            rasterio.band(src, 1),
            dst,
            dst_transform=transform,
            dst_crs="EPSG:3857",
            dst_nodata=-9999,
            resampling=Resampling.nearest,
        )
    west, north = transform.c, transform.f
    east, south = west + w * transform.a, north + h * transform.e
    lonlat = transform_bounds("EPSG:3857", "EPSG:4326", west, south, east, north)
    WEB.mkdir(parents=True, exist_ok=True)
    Image.fromarray(colourise(dst, WEB_ALPHA), "RGBA").save(WEB / f"{place['id']}.png", optimize=True)
    return {"id": place["id"], "image": f"ates/{place['id']}.png", "bounds": [round(v, 6) for v in lonlat]}


def nice_scale(metres_per_px: float, max_px: int) -> int:
    for m in (5000, 2000, 1000, 500, 200):
        if m / metres_per_px <= max_px:
            return m
    return 100


def print_map(place: dict, cls_path: Path, dem_path: Path, out: Path) -> None:
    cls, transform, crs = read_detail(cls_path, place["detail_bounds"])
    dem, _, _ = read_detail(dem_path, place["detail_bounds"])
    h, w = min(cls.shape[0], dem.shape[0]), min(cls.shape[1], dem.shape[1])
    cls, dem = cls[:h, :w], dem[:h, :w]
    cell = transform.a

    shade = hillshade(dem, cell)
    base = np.stack([200 + shade * 55] * 3, axis=-1)
    over = colourise(cls).astype("float32")
    a = (over[..., 3:4] / 255) * 0.7
    rgb = (base * (1 - a) + over[..., :3] * a).astype("uint8")

    page = Image.new("RGB", A4, "white")
    d = ImageDraw.Draw(page)
    margin, legend_w = 110, 900
    box = (margin, 330, A4[0] - legend_w - margin * 2, A4[1] - margin - 120)
    scale = min((box[2] - box[0]) / w, (box[3] - box[1]) / h)
    mw, mh = int(w * scale), int(h * scale)
    page.paste(Image.fromarray(rgb).resize((mw, mh), Image.NEAREST), (box[0], box[1]))
    d.rectangle((box[0], box[1], box[0] + mw, box[1] + mh), outline="#17283a", width=4)

    # Forecast points, with their elevation.
    for pt in place["points"]:
        (x,), (y,) = warp_points("EPSG:4326", crs, [pt["lon"]], [pt["lat"]])
        col, row = ~transform * (x, y)
        if 0 <= col < w and 0 <= row < h:
            px, py = box[0] + col * scale, box[1] + row * scale
            d.ellipse((px - 16, py - 16, px + 16, py + 16), fill="white", outline="#17283a", width=6)
            d.text(
                (px + 26, py - 26),
                f"{pt['elevation']} m",
                fill="#17283a",
                font=font(40, True),
                stroke_width=6,
                stroke_fill="white",
            )

    # Title and the draft banner.
    d.text((margin, 90), f"{place['name']['mk']} / {place['name']['en']}", fill="#17283a", font=font(84, True))
    d.text(
        (margin, 200),
        "Класи на лавински терен (ATES) · Avalanche terrain classes (ATES)",
        fill="#3d4a57",
        font=font(46),
    )
    banner = (A4[0] - legend_w - margin, 90, A4[0] - margin, 270)
    d.rectangle(banner, fill="#8c1610")
    d.text((banner[0] + 30, banner[1] + 22), "НАЦРТ · DRAFT", fill="white", font=font(64, True))
    d.text((banner[0] + 30, banner[1] + 105), "Непроверено · Not validated", fill="white", font=font(40))

    # Legend.
    lx, ly = A4[0] - legend_w - margin, 340
    for k in (1, 2, 3, 4, 0):
        c = CLASSES[k]
        fill = c["rgb"] or (255, 255, 255)
        d.rectangle((lx, ly, lx + 90, ly + 70), fill=fill, outline="#17283a", width=3)
        d.text((lx + 120, ly - 2), c["mk"], fill="#17283a", font=font(46, True))
        d.text((lx + 120, ly + 46), c["en"], fill="#3d4a57", font=font(36))
        ly += 150
    note = [
        "За разговор со водичи: каде е погрешно?",
        "For review with guides: where is it wrong?",
        "",
        "Не е за одлуки на терен. Модел (autoATES v3.0,",
        "западна Канада) на 30 m податоци; стрмни жлебови",
        "во шума и мали стрмни делови може да недостасуваат.",
        "",
        "Not for decisions in the field. A model (autoATES v3.0,",
        "western Canada) on 30 m data; steep gullies in forest",
        "and short steep sections may be missing.",
    ]
    for line in note:
        d.text((lx, ly), line, fill="#17283a", font=font(32))
        ly += 44

    # Scale bar and north arrow (UTM grid north; the difference to true north is under 1.5°).
    m_px = cell / scale
    bar_m = nice_scale(m_px, 600)
    bx, by = box[0] + 40, box[1] + mh - 90
    bar_px = int(bar_m / m_px)
    d.rectangle((bx - 20, by - 60, bx + bar_px + 40, by + 40), fill="white")
    d.rectangle((bx, by, bx + bar_px, by + 20), fill="#17283a")
    d.text(
        (bx, by - 52), f"{bar_m / 1000:g} km" if bar_m >= 1000 else f"{bar_m} m", fill="#17283a", font=font(36, True)
    )
    nx, ny = box[0] + mw - 90, box[1] + 60
    d.polygon([(nx, ny - 40), (nx - 28, ny + 40), (nx, ny + 20), (nx + 28, ny + 40)], fill="#17283a")
    d.text((nx - 14, ny + 46), "N", fill="#17283a", font=font(40, True))

    credits = (
        f"{date.today():%d.%m.%Y} · autoATES v3.0 (Sykes et al., ISSW 2026, MIT) · Copernicus DEM GLO-30 · "
        "© ESA WorldCover 2021 (CC BY 4.0) · Проект ЛавинОко / Project LavinOko"
    )
    d.text((margin, A4[1] - margin - 50), credits, fill="#3d4a57", font=font(30))

    out.parent.mkdir(parents=True, exist_ok=True)
    page.save(out.with_suffix(".png"), dpi=(DPI, DPI))
    page.save(out.with_suffix(".pdf"), resolution=DPI)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("places", nargs="*", default=["kozuf", "popova_sapka"])
    index = []
    for pid in ap.parse_args().places:
        place = next(p for p in REGIONS["places"] if p["id"] == pid)
        cls_path = CACHE / pid / "outputs" / "ATES" / "ATES_classification.tif"
        if not cls_path.exists():
            raise SystemExit(f"No AutoATES result for {pid}: run ates/run_autoates.sh")
        print_map(place, cls_path, CACHE / pid / "dem.tif", CACHE / "maps" / f"{pid}-draft-ates")
        index.append(web_overlay(place, cls_path))
        print(f"{pid}: print map and web overlay written")
    (WEB / "index.json").write_text(json.dumps({"draft": True, "areas": index}, indent=1))


if __name__ == "__main__":
    main()
