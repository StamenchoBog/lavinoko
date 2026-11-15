"""Fetch mountain weather for every place's forecast points and summarise it.

Usage:
    cd backend && uv run python weather/fetch_weather.py

Writes:
    frontend/static/data/weather.json   what the page shows (last 72 h, next 72 h), all places
    archive/weather/<time>.json         the full hourly forecast as issued, kept for
                                            checking forecasts against what actually happened

Source: Open-Meteo (https://open-meteo.com), free for non-commercial use, CC BY 4.0.
These are forecast-model values, not measurements.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # backend/, for the shared contract
from contract import ContractError, checked_json  # noqa: E402
from contract.models import Hourly, Sources, Weather  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]  # repository root
REGIONS = json.loads((ROOT / "config" / "regions.json").read_text())
WEB = ROOT / "frontend" / "static" / "data"  # weather.json for the website
ARCHIVE = ROOT / "archive" / "weather"

API = "https://api.open-meteo.com/v1/forecast"
HOURLY = [
    "temperature_2m",
    "snowfall",
    "rain",
    "wind_gusts_10m",
    "freezing_level_height",
    "snow_depth",
    # Free-air wind at pressure levels. Model wind near the ground is unreliable in
    # mountains (the model terrain is smoothed); the wind at ridge height is what moves snow.
    "wind_speed_850hPa",
    "wind_direction_850hPa",
    "wind_speed_800hPa",
    "wind_direction_800hPa",
    "wind_speed_700hPa",
    "wind_direction_700hPa",
]

# Pressure level closest to each elevation band (standard atmosphere, approximate).
WIND_LEVELS = [(1700, "850hPa"), (2400, "800hPa"), (99999, "700hPa")]


def wind_level(elevation: float) -> str:
    return next(level for top, level in WIND_LEVELS if elevation < top)


def select_wind(h: dict, elevation: float) -> dict:
    """Add 'wind_speed' and 'wind_direction' from the pressure level matching the elevation."""
    level = wind_level(elevation)
    return {**h, "wind_speed": h[f"wind_speed_{level}"], "wind_direction": h[f"wind_direction_{level}"]}


TZ = "Europe/Skopje"
WINDOW_H = 72

# Thresholds for plain weather facts. These are NOT avalanche danger criteria;
# they mark weather that forecasters everywhere pay attention to.
# Initial values, to be tuned with local guides after the first season.
T = {
    "heavy_snow_24h_cm": 20,
    "heavy_snow_72h_cm": 40,
    "recent_snow_72h_cm": 30,
    "drift_snow_24h_cm": 5,
    "drift_wind_kmh": 30,
    "strong_wind_kmh": 50,
    "rain_on_snow_mm": 5,
    "warming_after_snow_cm": 10,
    "warming_temp_c": 1,
}

COMPASS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]


def compass(deg: float) -> str:
    return COMPASS[int(((deg % 360) + 22.5) // 45) % 8]


def mean_direction(directions: list[float], weights: list[float]) -> float | None:
    """Weighted circular mean of wind directions in degrees."""
    x = sum(w * math.cos(math.radians(d)) for d, w in zip(directions, weights, strict=True))
    y = sum(w * math.sin(math.radians(d)) for d, w in zip(directions, weights, strict=True))
    if abs(x) < 1e-9 and abs(y) < 1e-9:
        return None
    return math.degrees(math.atan2(y, x)) % 360


# Independent models used to confirm alerts (all three provide ridge-height wind for North Macedonia).
# An alert is shown only when a majority of them raise it. See research/what-users-need.md.
CONSENSUS_MODELS = ["icon_eu", "gfs_seamless", "meteofrance_seamless"]
CONSENSUS_HOURLY = [
    "temperature_2m",
    "snowfall",
    "rain",
    "snow_depth",
    "wind_speed_850hPa",
    "wind_direction_850hPa",
    "wind_speed_800hPa",
    "wind_direction_800hPa",
    "wind_speed_700hPa",
    "wind_direction_700hPa",
]


def fetch(points: list[dict], models: list[str] | None = None, hourly: list[str] | None = None) -> list[dict]:
    """One request for all points. Returns one hourly series per point.

    With `models`, every variable comes back once per model, suffixed with the model name."""
    params = {
        "latitude": ",".join(str(p["lat"]) for p in points),
        "longitude": ",".join(str(p["lon"]) for p in points),
        # The elevation lets the service adjust temperature (and snow/rain split) to the point's
        # real height instead of the smoothed model terrain.
        "elevation": ",".join(str(p["elevation"]) for p in points),
        "hourly": ",".join(hourly or HOURLY),
        "past_days": 4,
        "forecast_days": 4,
        "timezone": TZ,
    }
    if models:
        params["models"] = ",".join(models)
    req = Request(
        f"{API}?{urlencode(params)}", headers={"User-Agent": "lavinoko/0.1 (+https://github.com/StamenchoBog/lavinoko)"}
    )
    with urlopen(req, timeout=60) as r:
        data = json.load(r)
    return data if isinstance(data, list) else [data]


def _sum(values) -> float:
    return round(sum(v or 0 for v in values), 1)


def _max(values) -> float | None:
    vals = [v for v in values if v is not None]
    return round(max(vals), 1) if vals else None


def _min(values) -> float | None:
    vals = [v for v in values if v is not None]
    return round(min(vals), 1) if vals else None


def now_index(times: list[str], now_local: datetime) -> int:
    """Index of the current hour in the series."""
    stamp = now_local.strftime("%Y-%m-%dT%H:00")
    if stamp in times:
        return times.index(stamp)
    # Fallback: last time not after now.
    return max(i for i, t in enumerate(times) if t <= stamp)


def wind_summary(h: dict, sl: slice) -> dict:
    speed, gust, direction = h["wind_speed"][sl], h["wind_gusts_10m"][sl], h["wind_direction"][sl]
    # Direction weighted by speed, only from hours with meaningful wind.
    pairs = [(d, s) for d, s in zip(direction, speed, strict=True) if d is not None and s is not None and s >= 15]
    mean_dir = mean_direction([p[0] for p in pairs], [p[1] for p in pairs]) if pairs else None
    return {
        "max_kmh": _max(speed),
        "gust_max_kmh": _max(gust),
        "from": compass(mean_dir) if mean_dir is not None else None,
        # Wind deposits snow on the lee side: slopes facing away from the wind.
        "loads": compass(mean_dir + 180) if mean_dir is not None else None,
    }


def summarise_point(h: dict, i_now: int) -> dict:
    past = slice(max(0, i_now - WINDOW_H), i_now)
    past24 = slice(max(0, i_now - 24), i_now)
    past12 = slice(max(0, i_now - 12), i_now)
    nxt = slice(i_now, i_now + WINDOW_H)
    nxt24 = slice(i_now, i_now + 24)
    return {
        # The patrol's morning question: what happened overnight?
        "past12": {
            "snow_cm": _sum(h["snowfall"][past12]),
            "rain_mm": _sum(h["rain"][past12]),
            "temp_min_c": _min(h["temperature_2m"][past12]),
            "wind": wind_summary(h, past12),
        },
        "past72": {
            "snow_cm": _sum(h["snowfall"][past]),
            "snow_24h_cm": _sum(h["snowfall"][past24]),
            "wind_24h_max_kmh": _max(h["wind_speed"][past24]),
            "temp_24h_min_c": _min(h["temperature_2m"][past24]),
            "rain_mm": _sum(h["rain"][past]),
            "temp_min_c": _min(h["temperature_2m"][past]),
            "temp_max_c": _max(h["temperature_2m"][past]),
            "wind": wind_summary(h, past),
        },
        "next72": {
            "snow_cm": _sum(h["snowfall"][nxt]),
            "snow_24h_cm": _sum(h["snowfall"][nxt24]),
            "rain_mm": _sum(h["rain"][nxt]),
            "temp_min_c": _min(h["temperature_2m"][nxt]),
            "temp_max_c": _max(h["temperature_2m"][nxt]),
            "freezing_level_min_m": _min(h["freezing_level_height"][nxt]),
            "freezing_level_max_m": _max(h["freezing_level_height"][nxt]),
            "wind": wind_summary(h, nxt),
        },
        "now": {
            "temp_c": h["temperature_2m"][i_now],
            "wind_kmh": h["wind_speed"][i_now],
            "wind_from": compass(h["wind_direction"][i_now]) if h["wind_direction"][i_now] is not None else None,
            "freezing_level_m": h["freezing_level_height"][i_now],
            "model_snow_depth_cm": round((h["snow_depth"][i_now] or 0) * 100),
        },
    }


def daily_rows(h: dict, i_now: int) -> list[dict]:
    """One row per calendar day, from 3 days ago to 3 days ahead."""
    days: dict[str, list[int]] = {}
    for i, t in enumerate(h["time"]):
        days.setdefault(t[:10], []).append(i)
    today = h["time"][i_now][:10]
    keys = sorted(days)
    k = keys.index(today)
    rows = []
    for day in keys[max(0, k - 3) : k + 4]:
        idx = days[day]
        speeds = [h["wind_speed"][i] for i in idx]
        dirs = [h["wind_direction"][i] for i in idx]
        pairs = [(d, s) for d, s in zip(dirs, speeds, strict=True) if d is not None and s is not None]
        mean_dir = mean_direction([p[0] for p in pairs], [p[1] for p in pairs]) if pairs else None
        rows.append(
            {
                "date": day,
                "when": "past" if day < today else ("today" if day == today else "future"),
                "snow_cm": _sum(h["snowfall"][i] for i in idx),
                "rain_mm": _sum(h["rain"][i] for i in idx),
                "temp_min_c": _min(h["temperature_2m"][i] for i in idx),
                "temp_max_c": _max(h["temperature_2m"][i] for i in idx),
                "wind_max_kmh": _max(speeds),
                "gust_max_kmh": _max(h["wind_gusts_10m"][i] for i in idx),
                "wind_from": compass(mean_dir) if mean_dir is not None else None,
                "freezing_min_m": _min(h["freezing_level_height"][i] for i in idx),
                "freezing_max_m": _max(h["freezing_level_height"][i] for i in idx),
            }
        )
    return rows


def drifting(h: dict, start: int, end: int) -> dict | None:
    """Any 24 h window with both new snow and strong wind -> drifting snow."""
    best = None
    for s in range(start, max(start, end - 24) + 1):
        sl = slice(s, s + 24)
        snow = _sum(h["snowfall"][sl])
        wind = _max(h["wind_speed"][sl]) or 0
        strong = snow >= T["drift_snow_24h_cm"] and wind >= T["drift_wind_kmh"]
        if strong and (best is None or snow * wind > best[0]):
            best = (snow * wind, sl, snow, wind)
    if best is None:
        return None
    w = wind_summary(h, best[1])
    return {"snow_cm": best[2], "wind_kmh": best[3], "from": w["from"], "loads": w["loads"]}


def flags_for(h: dict, i_now: int, summary: dict) -> list[dict]:
    """Plain weather facts worth attention. Codes are translated on the page."""
    p, n = summary["past72"], summary["next72"]
    flags: list[dict] = []
    if n["snow_24h_cm"] >= T["heavy_snow_24h_cm"] or n["snow_cm"] >= T["heavy_snow_72h_cm"]:
        flags.append({"code": "heavy_snow_coming", "snow_cm": n["snow_cm"], "snow_24h_cm": n["snow_24h_cm"]})
    if p["snow_cm"] >= T["recent_snow_72h_cm"]:
        flags.append({"code": "recent_heavy_snow", "snow_cm": p["snow_cm"]})
    for period, start, end in (("past", max(0, i_now - WINDOW_H), i_now), ("next", i_now, i_now + WINDOW_H)):
        d = drifting(h, start, min(end, len(h["time"])))
        if d:
            flags.append({"code": "wind_drifting", "period": period, **d})
    snow_on_ground = (h["snow_depth"][i_now] or 0) > 0 or p["snow_cm"] > 0
    # Wind is avalanche weather only when there is snow for it to move.
    if snow_on_ground or n["snow_cm"] > 0:
        for period, w in (("past", p["wind"]), ("next", n["wind"])):
            # Gusts are shown but do not trigger flags: model gusts in mountains are too noisy.
            if (w["max_kmh"] or 0) >= T["strong_wind_kmh"]:
                flags.append(
                    {
                        "code": "strong_wind",
                        "period": period,
                        "wind_kmh": w["max_kmh"],
                        "gust_kmh": w["gust_max_kmh"],
                        "from": w["from"],
                    }
                )
    if snow_on_ground and n["rain_mm"] >= T["rain_on_snow_mm"]:
        flags.append({"code": "rain_on_snow", "rain_mm": n["rain_mm"]})
    if p["snow_cm"] >= T["warming_after_snow_cm"] and (n["temp_max_c"] or -99) >= T["warming_temp_c"]:
        flags.append({"code": "warming_after_snow", "snow_cm": p["snow_cm"], "temp_max_c": n["temp_max_c"]})
    return flags


def split_models(hourly: dict, models: list[str], fallback: dict) -> dict[str, dict]:
    """Per-model hourly series from a multi-model response. Variables a model lacks are taken from
    `fallback` (the blended forecast), so every model can be run through the same flag logic."""
    out = {}
    for m in models:
        h = {"time": hourly["time"]}
        for key, values in hourly.items():
            if key.endswith("_" + m):
                h[key[: -len(m) - 1]] = values
        for key, values in fallback.items():
            if key not in h or all(v is None for v in h[key]):
                h[key] = values
        out[m] = h
    return out


# Which number represents each flag when picking the middle model.
FLAG_VALUE = {
    "heavy_snow_coming": "snow_cm",
    "recent_heavy_snow": "snow_cm",
    "wind_drifting": "snow_cm",
    "strong_wind": "wind_kmh",
    "rain_on_snow": "rain_mm",
    "warming_after_snow": "temp_max_c",
}


def consensus(model_flags: list[list[dict]]) -> list[dict]:
    """Keep a flag only if a majority of models raise it; "serious" only if a majority rate it serious.

    The shown values come from the middle model (median), with how many models agree."""
    n = len(model_flags)
    need = n // 2 + 1
    groups: dict[tuple, list[dict]] = {}
    for flags in model_flags:
        for f in flags:
            groups.setdefault((f["code"], f.get("period")), []).append(f)
    out = []
    for (code, _period), fs in groups.items():
        if len(fs) < need:
            continue
        fs = sorted(fs, key=lambda f: f.get(FLAG_VALUE[code]) or 0)
        rep = dict(fs[len(fs) // 2])
        serious = sum(f["level"] == "serious" for f in fs)
        rep["level"] = "serious" if serious >= need else "attention"
        rep["agree"] = len(fs)
        rep["models"] = n
        out.append(rep)
    order = {"serious": 0, "attention": 1}
    return sorted(out, key=lambda f: order[f["level"]])


MIN_COVERAGE = 0.9  # share of hours that must have a value


def required_vars(elevation: float) -> list[str]:
    """Variables the alerts depend on for a point at this elevation."""
    level = wind_level(elevation)
    return ["temperature_2m", "snowfall", "rain", f"wind_speed_{level}", f"wind_direction_{level}"]


def coverage(values: list | None) -> float:
    return sum(v is not None for v in values) / len(values) if values else 0.0


def check_blend(series: list[dict], points: list[dict]) -> list[str]:
    """Problems with the main forecast. Any problem means the run must not publish."""
    problems = []
    for s, p in zip(series, points, strict=True):
        for var in required_vars(p["elevation"]):
            if coverage(s.get("hourly", {}).get(var)) < MIN_COVERAGE:
                problems.append(f"{p['id']}@{p['elevation']}m: {var} missing")
    return problems


def check_models(ensemble: list[dict | None], points: list[dict], models: list[str]) -> dict[str, str]:
    """Per model: "ok", or the first reason it can't be trusted for alerts in this run."""
    status = {}
    for m in models:
        reason = "ok"
        for ens, p in zip(ensemble, points, strict=True):
            if ens is None:
                reason = "request failed"
                break
            for var in required_vars(p["elevation"]):
                if coverage(ens["hourly"].get(f"{var}_{m}")) < MIN_COVERAGE:
                    reason = f"no {var} at {p['elevation']} m"
                    break
            if reason != "ok":
                break
        status[m] = reason
    return status


def summarise_place_point(
    p: dict, s: dict, ens: dict | None, now_utc: datetime, models: list[str]
) -> tuple[dict, dict]:
    """Summary for the page, and the hourly series for the chart."""
    h = select_wind(s["hourly"], p["elevation"])
    now_local = now_utc + timedelta(seconds=s["utc_offset_seconds"])
    i = now_index(h["time"], now_local)
    summary = summarise_point(h, i)

    if ens is not None and len(models) >= 2:
        per_model = {
            m: select_wind(hm, p["elevation"]) for m, hm in split_models(ens["hourly"], models, s["hourly"]).items()
        }
        model_summaries = {m: summarise_point(hm, i) for m, hm in per_model.items()}
        flags = consensus([with_levels(flags_for(hm, i, model_summaries[m])) for m, hm in per_model.items()])
        rng = lambda get: [min(get(x) for x in model_summaries.values()), max(get(x) for x in model_summaries.values())]  # noqa: E731
        spread = {
            "models": models,
            "snow_next72_cm": rng(lambda x: x["next72"]["snow_cm"]),
            "snow_past72_cm": rng(lambda x: x["past72"]["snow_cm"]),
            "wind_next72_kmh": rng(lambda x: x["next72"]["wind"]["max_kmh"] or 0),
        }
    else:
        flags = with_levels(flags_for(h, i, summary))
        spread = None

    point = {
        "id": p["id"],
        "name": p["name"],
        "lon": p["lon"],
        "lat": p["lat"],
        "elevation": p["elevation"],
        "wind_level": wind_level(p["elevation"]),
        **summary,
        "spread": spread,
        "days": daily_rows(h, i),
        "flags": flags,
    }
    return point, {"id": p["id"], "elevation": p["elevation"], **hourly_window(h, i)}


# A flag is "serious" when it passes these stronger limits, otherwise "attention".
# Weather facts only — these are not avalanche danger levels. Initial values, to tune with guides.
SERIOUS = {
    "heavy_snow_coming": lambda f: f["snow_cm"] >= 50 or f["snow_24h_cm"] >= 30,
    "recent_heavy_snow": lambda f: f["snow_cm"] >= 50,
    "wind_drifting": lambda f: f["snow_cm"] >= 15 and f["wind_kmh"] >= 50,
    # Wind alone is never "serious": it matters for avalanches when it moves snow, which is
    # covered by wind_drifting. On its own it stays an "attention" item (exposure, closed lifts).
    "strong_wind": lambda f: False,
    "rain_on_snow": lambda f: f["rain_mm"] >= 15,
    "warming_after_snow": lambda f: f["snow_cm"] >= 20 and (f["temp_max_c"] or -99) >= 5,
}
LEVELS = ["none", "attention", "serious"]


def with_levels(flags: list[dict]) -> list[dict]:
    return [{**f, "level": "serious" if SERIOUS[f["code"]](f) else "attention"} for f in flags]


def place_level(points: list[dict]) -> str:
    """The most severe level among all forecast points of a place."""
    best = 0
    for pt in points:
        for f in pt["flags"]:
            best = max(best, LEVELS.index(f["level"]))
    return LEVELS[best]


def hourly_window(h: dict, i_now: int) -> dict:
    """Hourly series from 72 h before to 72 h after now, for the chart."""
    sl = slice(max(0, i_now - WINDOW_H), i_now + WINDOW_H)
    r = lambda xs: [None if v is None else round(v, 1) for v in xs[sl]]  # noqa: E731
    return {
        "time": h["time"][sl],
        "now_index": i_now - sl.start,
        "snow_cm": r(h["snowfall"]),
        "rain_mm": r(h["rain"]),
        "temp_c": r(h["temperature_2m"]),
        "wind_kmh": r(h["wind_speed"]),
        "wind_dir": [None if v is None else int(v) for v in h["wind_direction"][sl]],
        "freezing_m": [None if v is None else int(v) for v in h["freezing_level_height"][sl]],
    }


class DataError(RuntimeError):
    """The forecast data is unusable; nothing was published."""


def build(now_utc: datetime | None = None) -> dict:
    """One request for every forecast point of every place; one JSON for the whole country."""
    places = REGIONS["places"]
    flat = [(place, pt) for place in places for pt in place["points"]]
    pts = [pt for _, pt in flat]
    series = fetch(pts)
    problems = check_blend(series, pts)
    if problems:
        # Never replace a good forecast with a broken one: keep the last published files.
        raise DataError("Main forecast incomplete: " + "; ".join(problems[:5]))
    try:
        ensemble = fetch(pts, CONSENSUS_MODELS, CONSENSUS_HOURLY)
    except Exception as e:  # noqa: BLE001 — recorded in the health status below
        print(f"Consensus request failed: {e}")
        ensemble = [None] * len(pts)
    model_status = check_models(ensemble, pts, CONSENSUS_MODELS)
    healthy = [m for m, st in model_status.items() if st == "ok"]
    now_utc = now_utc or datetime.now(UTC)

    by_place: dict[str, list] = {}
    hourly: dict[str, list] = {}
    for (place, pt), s, ens in zip(flat, series, ensemble, strict=True):
        point, hours = summarise_place_point(pt, s, ens, now_utc, healthy)
        by_place.setdefault(place["id"], []).append(point)
        hourly.setdefault(place["id"], []).append(hours)

    out_places = []
    for place in places:
        pts = by_place[place["id"]]
        top = max(pts, key=lambda x: x["elevation"])
        out_places.append(
            {
                "id": place["id"],
                "kind": place["kind"],
                "pilot": place.get("pilot", False),
                "name": place["name"],
                "range": place["range"],
                "center": place["center"],
                "sources": place.get("sources", {}),
                "level": place_level(pts),
                # For the overview list: the highest point is the most exposed.
                "headline": {
                    "elevation": top["elevation"],
                    "snow_next72_cm": top["next72"]["snow_cm"],
                    "snow_past72_cm": top["past72"]["snow_cm"],
                    "wind_next72": top["next72"]["wind"],
                    "flag_count": len(top["flags"]),
                },
                "points": pts,
            }
        )

    issued = now_utc.replace(microsecond=0).isoformat()
    result = {
        "issued_utc": issued,
        "source": "Open-Meteo forecast models (CC BY 4.0)",
        "source_url": "https://open-meteo.com",
        "kind": "forecast_model",
        # Which models confirmed the alerts. Fewer than 2 healthy models = no model agreement:
        # alerts come from the blended forecast alone, and the page says so.
        "health": {"models": model_status, "consensus": len(healthy) >= 2},
        "thresholds": T,
        "places": out_places,
    }
    # Every file is checked against the data contract before any is written, so a run that would
    # break the page publishes nothing and the last good files stay.
    compact = {"separators": (",", ":")}
    try:
        files = {
            "weather.json": checked_json(Weather, result, **compact),
            # Hourly series per place, loaded only when someone opens that place.
            **{
                f"hourly/{pid}.json": checked_json(Hourly, {"issued_utc": issued, "points": pts}, **compact)
                for pid, pts in hourly.items()
            },
            # The source register travels with the data, so the page can show credits and licences.
            "sources.json": checked_json(Sources, json.loads((ROOT / "config" / "sources.json").read_text()), indent=1),
        }
    except ContractError as e:
        raise DataError(str(e)) from e
    (WEB / "hourly").mkdir(parents=True, exist_ok=True)
    for name, text in files.items():
        (WEB / name).write_text(text)

    # Keep the full hourly forecast as issued, for verification later.
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    raw = {
        "issued_utc": issued,
        "points": [
            {"place": place["id"], **pt, "hourly": s["hourly"]} for (place, pt), s in zip(flat, series, strict=True)
        ],
    }
    (ARCHIVE / f"{now_utc.strftime('%Y-%m-%dT%HZ')}.json").write_text(
        json.dumps(raw, ensure_ascii=False, separators=(",", ":"))
    )
    return result


def main() -> int:
    argparse.ArgumentParser(description="Fetch and summarise mountain weather for all places.").parse_args()
    try:
        r = build()
    except DataError as e:
        print(f"::error::{e}")  # shown as an error annotation in GitHub Actions
        return 1
    for m, st in r["health"]["models"].items():
        if st != "ok":
            print(f"::warning::Model {m} not used for alerts: {st}")
    if not r["health"]["consensus"]:
        print("::error::Fewer than 2 healthy models: alerts published without model agreement")
    for place in r["places"]:
        hl = place["headline"]
        print(f"{place['id']:15} top {hl['elevation']} m: next 72 h {hl['snow_next72_cm']} cm, level {place['level']}")
    return 0 if r["health"]["consensus"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
