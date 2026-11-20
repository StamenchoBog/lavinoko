"""Compare archived forecasts with what happened, by lead time and by model.

Usage:
    cd backend && uv run python verify/verify.py --archive ../../lavinoko-archive/weather [--since 2026-11-15]
        [--until 2027-06-30] [--reference stations.csv] [--out report.md] [--pairs pairs.csv]

Reads every forecast run in the archive (StamenchoBog/lavinoko-archive, cloned locally), and for each forecast
point, each source (the blend the website shows, and each model) and each lead day (hours 0–24, 24–48, 48–72
after the issue) compares:

    temperature_2m  hourly: bias and mean absolute error (°C)
    snowfall        24-hour sums: bias and mean absolute error (cm), and whether a snow day (>= 5 cm) and
                    a heavy-snow day (the run's own heavy_snow_24h_cm threshold) were forecast and happened
    rain            24-hour sums: bias and mean absolute error (mm)

Ridge-height wind (the 850/800/700 hPa wind the site shows) is not verified: ERA5 on Open-Meteo has no
pressure-level wind, and no station measures it.

Reference ("what happened"):
    default         ERA5 reanalysis from Open-Meteo's historical weather API: independent of the three forecast
                    models, but a ~25 km grid. Temperature is adjusted to each point's height; snow and rain are
                    the grid cell's, so they are smoothed and usually too low on the mountain. Use it to compare
                    sources and lead times, not as the truth on the mountain. Available ~6 days after the fact.
    --reference     a CSV of measurements, once there are any (UHMR stations, the resort, own observations):
                        place,point,time_utc,variable,value
                        kozuf,summit,2027-01-10T06:00,temperature_2m,-7.4
                    `variable` is temperature_2m (°C), snowfall (cm in the hour ending at time_utc) or rain (mm).

A lead day is used only where forecast and reference both have all 24 hours.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import sys
from collections import defaultdict
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "weather"))
from fetch_weather import get_json  # noqa: E402

CACHE = Path(__file__).resolve().parents[1] / ".cache" / "verify"
ERA5_API = "https://archive-api.open-meteo.com/v1/archive"
UA = {"User-Agent": "lavinoko/0.1 (+https://github.com/StamenchoBog/lavinoko)"}

VARIABLES = ("temperature_2m", "snowfall", "rain")
SUMMED = ("snowfall", "rain")
LEAD_DAYS = (1, 2, 3)
SNOW_DAY_CM = 5.0
SOURCE_NAMES = {
    "blend": "Website (blend)",
    "icon_eu": "ICON-EU",
    "gfs_seamless": "GFS",
    "meteofrance_seamless": "Météo-France",
}

PointKey = tuple[str, str]  # (place, point id)
Reference = dict[PointKey, dict[datetime, dict[str, float]]]


# --- Archive -----------------------------------------------------------------------------------------------


def run_files(archive: Path, since: date | None, until: date | None) -> list[Path]:
    """Archive files (weather/YYYY/MM/YYYY-MM-DDTHHZ.json.gz) issued between since and until, inclusive."""
    files = []
    for f in sorted(archive.glob("*/*/*.json.gz")):
        day = date.fromisoformat(f.name[:10])
        if (since is None or day >= since) and (until is None or day <= until):
            files.append(f)
    return files


def load_run(path: Path) -> dict:
    return json.loads(gzip.decompress(path.read_bytes()))


def utc_times(local: list[str], tz: str) -> list[datetime]:
    zone = ZoneInfo(tz)
    return [datetime.fromisoformat(t).replace(tzinfo=zone).astimezone(UTC) for t in local]


def sources(point: dict) -> Iterator[tuple[str, dict[str, list]]]:
    """(source, {variable: values}) for the blend and each model that has data in this run."""
    yield "blend", {v: point["hourly"].get(v) or [] for v in VARIABLES}
    models = point.get("models_hourly") or {}
    for model in SOURCE_NAMES:
        if model != "blend" and f"temperature_2m_{model}" in models:
            yield model, {v: models.get(f"{v}_{model}") or [] for v in VARIABLES}


# --- Reference ---------------------------------------------------------------------------------------------


def read_reference_csv(path: Path) -> Reference:
    ref: Reference = defaultdict(lambda: defaultdict(dict))
    with path.open(newline="") as f:
        for row in csv.DictReader(f):
            if row["variable"] not in VARIABLES or row["value"] == "":
                continue
            t = datetime.fromisoformat(row["time_utc"]).replace(tzinfo=UTC)
            ref[(row["place"], row["point"])][t][row["variable"]] = float(row["value"])
    return ref


def months(start: date, end: date) -> list[date]:
    out, m = [], start.replace(day=1)
    while m <= end:
        out.append(m)
        m = (m + timedelta(days=32)).replace(day=1)
    return out


def era5_month(points: dict[PointKey, dict], month: date, today: date) -> list[dict]:
    """ERA5 hourly series (UTC) for every point in one month. Complete months are cached in .cache/verify/."""
    last = (month + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    keys = sorted(points)
    cache = CACHE / f"era5-{month:%Y-%m}.json"
    if cache.exists():
        cached = json.loads(cache.read_text())
        if cached["points"] == [list(k) for k in keys]:
            return cached["series"]
    params = {
        "latitude": ",".join(str(points[k]["lat"]) for k in keys),
        "longitude": ",".join(str(points[k]["lon"]) for k in keys),
        "elevation": ",".join(str(points[k]["elevation"]) for k in keys),
        "start_date": month.isoformat(),
        "end_date": min(last, today).isoformat(),
        "hourly": ",".join(VARIABLES),
        "models": "era5",
        "timezone": "GMT",
    }
    data = get_json(Request(f"{ERA5_API}?{urlencode(params)}", headers=UA))
    series = [d["hourly"] for d in (data if isinstance(data, list) else [data])]
    # ERA5 arrives ~6 days late: only a month that ended well before today is complete and worth keeping.
    if last <= today - timedelta(days=10):
        CACHE.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps({"points": [list(k) for k in keys], "series": series}))
    return series


def era5_reference(points: dict[PointKey, dict], start: date, end: date, today: date) -> Reference:
    ref: Reference = defaultdict(lambda: defaultdict(dict))
    keys = sorted(points)
    for month in months(start, min(end, today)):
        for key, h in zip(keys, era5_month(points, month, today), strict=True):
            for i, t in enumerate(h["time"]):
                when = datetime.fromisoformat(t).replace(tzinfo=UTC)
                for v in VARIABLES:
                    if h[v][i] is not None:
                        ref[key][when][v] = h[v][i]
    return ref


# --- Scores ------------------------------------------------------------------------------------------------


@dataclass
class Errors:
    """Forecast minus reference, collected for one variable, source and lead day."""

    diffs: list[float] = field(default_factory=list)

    def add(self, forecast: float, observed: float) -> None:
        self.diffs.append(forecast - observed)

    @property
    def n(self) -> int:
        return len(self.diffs)

    @property
    def bias(self) -> float:
        return sum(self.diffs) / self.n

    @property
    def mae(self) -> float:
        return sum(abs(d) for d in self.diffs) / self.n


@dataclass
class Events:
    """Yes/no forecasts of an event (e.g. a heavy-snow day) against what happened."""

    hits: int = 0
    misses: int = 0
    false_alarms: int = 0
    quiet: int = 0

    def add(self, forecast: bool, observed: bool) -> None:
        if forecast and observed:
            self.hits += 1
        elif observed:
            self.misses += 1
        elif forecast:
            self.false_alarms += 1
        else:
            self.quiet += 1


@dataclass
class Scores:
    errors: dict[tuple[str, str, int], Errors] = field(default_factory=lambda: defaultdict(Errors))
    events: dict[tuple[str, str, int], Events] = field(default_factory=lambda: defaultdict(Events))
    runs: int = 0
    first: str = ""
    last: str = ""


def window(times: list[datetime], start: datetime) -> list[int]:
    """Indexes of the 24 hours from start, or [] if the series does not cover them all."""
    idx = [i for i, t in enumerate(times) if start <= t < start + timedelta(hours=24)]
    return idx if len(idx) == 24 else []


def score_run(run: dict, ref: Reference, scores: Scores, pairs: list[dict] | None = None) -> None:
    issued = datetime.fromisoformat(run["issued_utc"]).astimezone(UTC).replace(minute=0, second=0, microsecond=0)
    heavy_cm = float(run.get("thresholds", {}).get("heavy_snow_24h_cm", 20))
    scores.runs += 1
    scores.first = scores.first or run["issued_utc"]
    scores.last = run["issued_utc"]
    for point in run["points"]:
        observed = ref.get((point["place"], point["id"]))
        if not observed:
            continue
        times = utc_times(point["hourly"]["time"], run.get("timezone", "Europe/Skopje"))
        for source, values in sources(point):
            for lead in LEAD_DAYS:
                start = issued + timedelta(hours=24 * (lead - 1))
                idx = window(times, start)
                if not idx:
                    continue
                for v in VARIABLES:
                    fc = [values[v][i] if i < len(values[v]) else None for i in idx]
                    ob = [observed.get(times[i], {}).get(v) for i in idx]
                    if None in fc or None in ob:
                        continue
                    key = (v, source, lead)
                    if v in SUMMED:
                        f, o = sum(fc), sum(ob)
                        scores.errors[key].add(f, o)
                        if v == "snowfall":
                            scores.events[("snow_day", source, lead)].add(f >= SNOW_DAY_CM, o >= SNOW_DAY_CM)
                            scores.events[("heavy_snow", source, lead)].add(f >= heavy_cm, o >= heavy_cm)
                    else:
                        f, o = sum(fc) / 24, sum(ob) / 24
                        for a, b in zip(fc, ob, strict=True):
                            scores.errors[key].add(a, b)
                    if pairs is not None:
                        pairs.append(
                            {
                                "issued_utc": run["issued_utc"],
                                "place": point["place"],
                                "point": point["id"],
                                "source": source,
                                "lead_day": lead,
                                "variable": v,
                                "forecast": round(f, 2),
                                "observed": round(o, 2),
                            }
                        )


# --- Report ------------------------------------------------------------------------------------------------


def _ratio(a: int, b: int) -> str:
    return f"{a / b:.0%}" if b else "–"


def report(scores: Scores, reference_label: str, heavy_cm: float) -> str:
    out = [
        "# Forecast verification",
        "",
        f"{scores.runs} archived runs, issued {scores.first[:16]} to {scores.last[:16]} UTC. "
        f"Reference: {reference_label}.",
        "",
        "Bias is forecast minus reference (positive: forecast too high). MAE is the mean absolute error. "
        "Day 1 is the first 24 hours after the issue. n counts hours for temperature and 24-hour periods otherwise.",
        "",
    ]
    units = {"temperature_2m": "°C, hourly", "snowfall": "cm per 24 h", "rain": "mm per 24 h"}
    for v in VARIABLES:
        out += [
            f"## {v} ({units[v]})",
            "",
            "| Source | " + " | ".join(f"Day {d} bias | Day {d} MAE" for d in LEAD_DAYS) + " | n (day 1) |",
            "|---|" + "---:|---:|" * len(LEAD_DAYS) + "---:|",
        ]
        for source, label in SOURCE_NAMES.items():
            cells = []
            for d in LEAD_DAYS:
                e = scores.errors.get((v, source, d))
                cells += [f"{e.bias:+.1f}", f"{e.mae:.1f}"] if e and e.n else ["–", "–"]
            n = scores.errors.get((v, source, 1))
            out.append(f"| {label} | " + " | ".join(cells) + f" | {n.n if n else 0} |")
        out.append("")
    for event, title in (
        ("snow_day", f"Snow days (>= {SNOW_DAY_CM:g} cm in 24 h)"),
        ("heavy_snow", f"Heavy-snow days (>= {heavy_cm:g} cm in 24 h, the alert threshold)"),
    ):
        out += [
            f"## {title}",
            "",
            "Hit rate: share of observed events that were forecast. False alarms: share of forecast events that did not happen.",
            "",
            "| Source | Lead day | Observed | Forecast | Hits | Hit rate | False alarms |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
        for source, label in SOURCE_NAMES.items():
            for d in LEAD_DAYS:
                ev = scores.events.get((event, source, d))
                if not ev:
                    continue
                observed, forecast = ev.hits + ev.misses, ev.hits + ev.false_alarms
                out.append(
                    f"| {label} | {d} | {observed} | {forecast} | {ev.hits} | {_ratio(ev.hits, observed)} "
                    f"| {_ratio(ev.false_alarms, forecast)} |"
                )
        out.append("")
    out += [
        "Ridge-height wind is not verified (no reference). These are weather forecasts, not avalanche danger ratings.",
        "",
    ]
    return "\n".join(out)


# --- Main --------------------------------------------------------------------------------------------------


def unique_points(runs: Iterable[dict]) -> dict[PointKey, dict]:
    points: dict[PointKey, dict] = {}
    for run in runs:
        for p in run["points"]:
            points[(p["place"], p["id"])] = {"lat": p["lat"], "lon": p["lon"], "elevation": p["elevation"]}
    return points


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--archive", type=Path, required=True, help="the weather/ folder of a lavinoko-archive clone")
    ap.add_argument("--since", type=date.fromisoformat, help="first issue day (default: all)")
    ap.add_argument("--until", type=date.fromisoformat, help="last issue day (default: all)")
    ap.add_argument("--reference", type=Path, help="CSV of measurements instead of ERA5 (see above)")
    ap.add_argument("--out", type=Path, help="write the report here (default: print it)")
    ap.add_argument("--pairs", type=Path, help="also write every forecast/reference pair to this CSV")
    args = ap.parse_args()

    files = run_files(args.archive, args.since, args.until)
    if not files:
        print(f"No archive files in {args.archive}", file=sys.stderr)
        return 1
    print(f"{len(files)} runs", file=sys.stderr)

    if args.reference:
        ref, label = read_reference_csv(args.reference), f"measurements from {args.reference.name}"
    else:
        # Points rarely change; reading only the first and last run keeps this fast.
        points = unique_points(load_run(f) for f in (files[0], files[-1]))
        start = date.fromisoformat(files[0].name[:10])
        end = date.fromisoformat(files[-1].name[:10]) + timedelta(days=4)
        ref = era5_reference(points, start, end, datetime.now(UTC).date())
        label = "ERA5 reanalysis (Open-Meteo, ~25 km grid; temperature adjusted to point height)"

    scores, pairs, heavy_cm = Scores(), [] if args.pairs else None, 20.0
    for f in files:
        run = load_run(f)
        heavy_cm = float(run.get("thresholds", {}).get("heavy_snow_24h_cm", heavy_cm))
        score_run(run, ref, scores, pairs)

    text = report(scores, label, heavy_cm)
    if args.out:
        args.out.write_text(text)
        print(f"Wrote {args.out}", file=sys.stderr)
    else:
        print(text)
    if args.pairs and pairs:
        with args.pairs.open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(pairs[0]))
            w.writeheader()
            w.writerows(pairs)
        print(f"Wrote {args.pairs} ({len(pairs)} rows)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
