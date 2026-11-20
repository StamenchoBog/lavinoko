import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "verify"))
from verify import Scores, months, read_reference_csv, report, score_run, utc_times, window  # noqa: E402

ISSUED = datetime(2026, 12, 1, 6, 18, tzinfo=UTC)


def run(temp=-5.0, snow=0.0, rain=0.0, gfs_temp=None, hours=8 * 24):
    """One archived run: one point, 8 days of hourly local times starting 4 days before the issue."""
    start_local = datetime(2026, 11, 27, 0, 0)  # Europe/Skopje, UTC+1 in winter
    times = [(start_local + timedelta(hours=i)).strftime("%Y-%m-%dT%H:%M") for i in range(hours)]
    hourly = {"time": times, "temperature_2m": [temp] * hours, "snowfall": [snow] * hours, "rain": [rain] * hours}
    models = {"time": times}
    if gfs_temp is not None:
        models |= {
            "temperature_2m_gfs_seamless": [gfs_temp] * hours,
            "snowfall_gfs_seamless": [snow] * hours,
            "rain_gfs_seamless": [rain] * hours,
        }
    return {
        "issued_utc": ISSUED.isoformat(),
        "timezone": "Europe/Skopje",
        "thresholds": {"heavy_snow_24h_cm": 20},
        "points": [
            {
                "place": "kozuf",
                "id": "summit",
                "lat": 41.16,
                "lon": 22.21,
                "elevation": 2170,
                "hourly": hourly,
                "models_hourly": models,
            }
        ],
    }


def reference(temp=-7.0, snow=0.0, rain=0.0, until_hours=80):
    """Observed values from the issue hour on, hourly, in UTC."""
    t0 = ISSUED.replace(minute=0)
    return {
        ("kozuf", "summit"): {
            t0 + timedelta(hours=i): {"temperature_2m": temp, "snowfall": snow, "rain": rain}
            for i in range(until_hours)
        }
    }


def test_local_times_become_utc_across_the_season():
    assert utc_times(["2026-12-01T07:00", "2026-07-01T08:00"], "Europe/Skopje") == [
        datetime(2026, 12, 1, 6, tzinfo=UTC),
        datetime(2026, 7, 1, 6, tzinfo=UTC),
    ]


def test_window_needs_all_24_hours():
    times = [datetime(2026, 12, 1, tzinfo=UTC) + timedelta(hours=i) for i in range(30)]
    assert len(window(times, times[0])) == 24
    assert window(times, times[10]) == []


def test_temperature_bias_and_error_per_lead_day_and_model():
    scores = Scores()
    score_run(run(temp=-5.0, gfs_temp=-9.0), reference(temp=-7.0), scores)
    blend = scores.errors[("temperature_2m", "blend", 1)]
    assert blend.n == 24 and blend.bias == 2.0 and blend.mae == 2.0
    gfs = scores.errors[("temperature_2m", "gfs_seamless", 3)]
    assert gfs.bias == -2.0 and gfs.mae == 2.0


def test_lead_days_without_a_full_reference_are_skipped():
    scores = Scores()
    score_run(run(), reference(until_hours=50), scores)  # covers day 1 and 2 only
    assert ("temperature_2m", "blend", 2) in scores.errors
    assert ("temperature_2m", "blend", 3) not in scores.errors


def test_snow_is_compared_as_24_hour_sums_with_events():
    scores = Scores()
    # Forecast 1 cm/h = 24 cm a day (a heavy-snow day); observed 0.25 cm/h = 6 cm (a snow day, not heavy).
    score_run(run(snow=1.0), reference(snow=0.25), scores)
    e = scores.errors[("snowfall", "blend", 1)]
    assert e.n == 1 and e.bias == 18.0
    assert scores.events[("snow_day", "blend", 1)].hits == 1
    heavy = scores.events[("heavy_snow", "blend", 1)]
    assert heavy.false_alarms == 1 and heavy.hits == 0


def test_points_without_reference_are_ignored():
    scores = Scores()
    score_run(run(), {}, scores)
    assert scores.runs == 1 and not scores.errors


def test_report_lists_every_source_and_says_what_it_is_not():
    scores = Scores()
    score_run(run(gfs_temp=-6.0), reference(), scores)
    text = report(scores, "test", 20)
    assert "| Website (blend) | +2.0 | 2.0 |" in text
    assert "| GFS | +1.0 | 1.0 |" in text
    assert "| ICON-EU | – | – |" in text
    assert "not avalanche danger ratings" in text


def test_measurements_csv(tmp_path):
    f = tmp_path / "stations.csv"
    f.write_text(
        "place,point,time_utc,variable,value\n"
        "kozuf,summit,2027-01-10T06:00,temperature_2m,-7.4\n"
        "kozuf,summit,2027-01-10T06:00,snowfall,\n"
        "kozuf,summit,2027-01-10T06:00,wind_speed,40\n"
    )
    ref = read_reference_csv(f)
    assert ref[("kozuf", "summit")] == {datetime(2027, 1, 10, 6, tzinfo=UTC): {"temperature_2m": -7.4}}


def test_months_span():
    assert months(date(2026, 11, 15), date(2027, 1, 3)) == [date(2026, 11, 1), date(2026, 12, 1), date(2027, 1, 1)]
