import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "weather"))
from fetch_weather import (  # noqa: E402
    compass,
    daily_rows,
    flags_for,
    mean_direction,
    now_index,
    summarise_point,
)


def series(hours=168, **overrides):
    """Synthetic hourly series starting 2026-01-10T00:00, calm and dry by default."""
    from datetime import datetime, timedelta

    t0 = datetime(2026, 1, 10)
    h = {
        "time": [(t0 + timedelta(hours=i)).strftime("%Y-%m-%dT%H:00") for i in range(hours)],
        "temperature_2m": [-5.0] * hours,
        "snowfall": [0.0] * hours,
        "rain": [0.0] * hours,
        "wind_speed": [5.0] * hours,
        "wind_direction": [0] * hours,
        "wind_gusts_10m": [10.0] * hours,
        "freezing_level_height": [1000.0] * hours,
        "snow_depth": [0.5] * hours,
    }
    for key, fn in overrides.items():
        h[key] = [fn(i, v) for i, v in enumerate(h[key])]
    return h


NOW = 84  # 2026-01-13T12:00, with 84 h before and 84 h after


def codes(h):
    return [f["code"] for f in flags_for(h, NOW, summarise_point(h, NOW))]


def test_compass_and_mean_direction():
    assert compass(0) == "N" and compass(350) == "N" and compass(135) == "SE" and compass(292) == "W"
    # Mean of 350° and 10° is north, not south.
    assert round(mean_direction([350, 10], [1, 1])) % 360 == 0


def test_now_index():
    h = series()
    from datetime import datetime

    assert now_index(h["time"], datetime(2026, 1, 13, 12, 30)) == NOW


def test_calm_weather_has_no_flags():
    assert codes(series()) == []


def test_heavy_snow_coming():
    h = series(snowfall=lambda i, v: 1.0 if NOW <= i < NOW + 30 else v)
    s = summarise_point(h, NOW)
    assert s["next72"]["snow_cm"] == 30.0
    assert s["next72"]["snow_24h_cm"] == 24.0
    assert "heavy_snow_coming" in codes(h)


def test_snow_with_northwest_wind_loads_southeast_slopes():
    h = series(
        snowfall=lambda i, v: 0.5 if NOW - 20 <= i < NOW else v,
        wind_speed=lambda i, v: 45.0 if NOW - 20 <= i < NOW else v,
        wind_direction=lambda i, v: 315 if NOW - 20 <= i < NOW else v,
    )
    flags = flags_for(h, NOW, summarise_point(h, NOW))
    drift = [f for f in flags if f["code"] == "wind_drifting"]
    assert drift and drift[0]["period"] == "past"
    assert drift[0]["from"] == "NW" and drift[0]["loads"] == "SE"


def test_rain_on_snow():
    h = series(rain=lambda i, v: 1.0 if NOW + 5 <= i < NOW + 15 else v)
    assert "rain_on_snow" in codes(h)


def test_warming_after_snow():
    h = series(
        snowfall=lambda i, v: 1.0 if NOW - 15 <= i < NOW else v,
        temperature_2m=lambda i, v: 4.0 if NOW + 20 <= i < NOW + 26 else v,
    )
    assert "warming_after_snow" in codes(h)


def test_daily_rows_cover_three_days_each_side():
    rows = daily_rows(series(), NOW)
    assert [r["when"] for r in rows] == ["past"] * 3 + ["today"] + ["future"] * 3
    assert rows[3]["date"] == "2026-01-13"


def test_wind_level_by_elevation():
    from fetch_weather import wind_level

    assert wind_level(1610) == "850hPa" and wind_level(2170) == "800hPa" and wind_level(2750) == "700hPa"


def test_flag_levels():
    from fetch_weather import place_level, with_levels

    mild = with_levels([{"code": "strong_wind", "wind_kmh": 55, "gust_kmh": 80, "from": "W"}])
    hard = with_levels([{"code": "heavy_snow_coming", "snow_cm": 60, "snow_24h_cm": 25}])
    assert mild[0]["level"] == "attention" and hard[0]["level"] == "serious"
    assert place_level([{"flags": []}]) == "none"
    assert place_level([{"flags": mild}, {"flags": hard}]) == "serious"


def test_hourly_window_is_centred_on_now():
    from fetch_weather import hourly_window

    h = series()
    w = hourly_window(h, NOW)
    assert w["time"][w["now_index"]] == h["time"][NOW]
    assert len(w["time"]) == 144


def test_strong_wind_without_snow_is_not_flagged():
    bare = series(wind_speed=lambda i, v: 80.0, snow_depth=lambda i, v: 0.0)
    snowy = series(wind_speed=lambda i, v: 80.0)
    assert "strong_wind" not in codes(bare)
    assert "strong_wind" in codes(snowy)


def test_consensus_needs_a_majority():
    from fetch_weather import consensus

    wind = lambda v, lvl="attention": {"code": "strong_wind", "period": "next", "wind_kmh": v, "level": lvl}  # noqa: E731
    snow = lambda v, lvl: {"code": "heavy_snow_coming", "snow_cm": v, "snow_24h_cm": v / 2, "level": lvl}  # noqa: E731
    # Only one of three models sees strong wind: no alert.
    assert consensus([[wind(60)], [], []]) == []
    # Two of three: alert, with the middle value and the agreement count.
    out = consensus([[wind(60)], [wind(80)], []])
    assert len(out) == 1 and out[0]["agree"] == 2 and out[0]["models"] == 3
    # Serious only when a majority rate it serious.
    one_serious = consensus([[snow(60, "serious")], [snow(42, "attention")], [snow(41, "attention")]])
    assert one_serious[0]["level"] == "attention" and one_serious[0]["snow_cm"] == 42
    two_serious = consensus([[snow(60, "serious")], [snow(55, "serious")], [snow(41, "attention")]])
    assert two_serious[0]["level"] == "serious"


def test_split_models_fills_missing_variables_from_blend():
    from fetch_weather import split_models

    hourly = {
        "time": ["t0"],
        "snowfall_icon_eu": [1.0],
        "snowfall_gfs_seamless": [2.0],
        "snow_depth_gfs_seamless": [None],
    }
    fallback = {"time": ["t0"], "snowfall": [9.0], "snow_depth": [0.4]}
    per = split_models(hourly, ["icon_eu", "gfs_seamless"], fallback)
    assert per["icon_eu"]["snowfall"] == [1.0] and per["gfs_seamless"]["snowfall"] == [2.0]
    assert per["gfs_seamless"]["snow_depth"] == [0.4]  # missing in model -> blend


def test_model_health_detects_empty_variable():
    from fetch_weather import check_models

    good = {
        "hourly": {
            f"{v}_a": [1.0] * 10
            for v in ["temperature_2m", "snowfall", "rain", "wind_speed_800hPa", "wind_direction_800hPa"]
        }
    }
    good["hourly"].update(
        {f"{v}_b": [1.0] * 10 for v in ["temperature_2m", "snowfall", "rain", "wind_direction_800hPa"]}
    )
    good["hourly"]["wind_speed_800hPa_b"] = [None] * 10  # model b silently lacks ridge wind
    status = check_models([good], [{"id": "x", "elevation": 2170}], ["a", "b"])
    assert status["a"] == "ok"
    assert status["b"].startswith("no wind_speed_800hPa")
    assert check_models([None], [{"id": "x", "elevation": 2170}], ["a"])["a"] == "request failed"


def test_broken_main_forecast_is_not_published():
    from fetch_weather import check_blend

    s = {
        "hourly": {
            "temperature_2m": [1.0] * 10,
            "snowfall": [None] * 10,
            "rain": [0.0] * 10,
            "wind_speed_850hPa": [5.0] * 10,
            "wind_direction_850hPa": [90] * 10,
        }
    }
    assert check_blend([s], [{"id": "x", "elevation": 1600}]) == ["x@1600m: snowfall missing"]


def test_consensus_with_two_models():
    from fetch_weather import consensus

    wind = {"code": "strong_wind", "period": "next", "wind_kmh": 60, "level": "attention"}
    assert consensus([[wind], []]) == []  # 2 models: both must agree
    assert consensus([[wind], [wind]])[0]["models"] == 2


def test_archive_keeps_blend_and_each_model_gzipped(tmp_path):
    import gzip
    import json
    from datetime import UTC, datetime

    from fetch_weather import archive_record, write_archive

    place = {"id": "kozuf"}
    pt = {"id": "summit", "lon": 22.2, "lat": 41.17, "elevation": 2170}
    blend = {"hourly": {"time": ["2026-01-10T00:00"], "snowfall": [1.0]}}
    models = {"hourly": {"time": ["2026-01-10T00:00"], "snowfall_icon_eu": [1.2]}}
    now = datetime(2026, 1, 10, 6, 17, tzinfo=UTC)

    rec = archive_record("2026-01-10T06:17:00+00:00", [(place, pt)], [blend], [models], {"icon_eu": "ok"})
    path = write_archive(rec, tmp_path, now)

    assert path == tmp_path / "2026" / "01" / "2026-01-10T06Z.json.gz"
    back = json.loads(gzip.decompress(path.read_bytes()))
    assert back["points"][0]["hourly"]["snowfall"] == [1.0]
    assert back["points"][0]["models_hourly"]["snowfall_icon_eu"] == [1.2]
    assert back["models"]["health"] == {"icon_eu": "ok"}
    # Same content, same bytes: a repeated run does not show up as a change in git.
    assert write_archive(rec, tmp_path, now).read_bytes() == path.read_bytes()


def test_archive_records_a_failed_model_request_as_null():
    from fetch_weather import archive_record

    rec = archive_record("t", [({"id": "p"}, {"id": "x"})], [{"hourly": {}}], [None], {})
    assert rec["points"][0]["models_hourly"] is None
