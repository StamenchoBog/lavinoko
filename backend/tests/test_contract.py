"""The data contract: backend output, test data and the generated frontend files all agree."""

import json
import sys
import typing
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from pydantic import TypeAdapter

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(BACKEND / "weather"))
from fetch_weather import SERIOUS, summarise_place_point  # noqa: E402

from contract import ContractError, checked_json  # noqa: E402
from contract.generate import outputs  # noqa: E402
from contract.models import ROOTS, Flag, HourlyPoint, Sources, Weather, WeatherPoint  # noqa: E402

ROOT = BACKEND.parent
FIXTURES = ROOT / "frontend" / "tests" / "fixtures" / "data"
FLAG_CODES = {typing.get_args(m.model_fields["code"].annotation)[0] for m in typing.get_args(Flag.__value__.__origin__)}


def test_generated_frontend_files_are_up_to_date():
    for path, text in outputs().items():
        assert path.read_text() == text, f"{path.name} is stale: run `cd backend && uv run python -m contract.generate`"


@pytest.mark.parametrize(
    ("name", "file"),
    [
        ("weather", "weather.json"),
        ("hourly", "hourly/korab.json"),
        ("sources", "sources.json"),
        ("terrain", "terrain/metadata.json"),
    ],
)
def test_frontend_test_data_matches_the_contract(name, file):
    ROOTS[name].model_validate_json((FIXTURES / file).read_text())


def test_source_register_matches_the_contract():
    Sources.model_validate_json((ROOT / "config" / "sources.json").read_text())


def test_every_flag_code_has_a_contract_type():
    assert set(SERIOUS) == FLAG_CODES


def raw_series(hours=192):
    """Open-Meteo-like hourly series in which every flag fires; now is hour 96."""
    t0 = datetime(2026, 1, 10)
    now = 96
    past = lambda i: now - 72 <= i < now  # noqa: E731
    snow_next = lambda i: now <= i < now + 30  # noqa: E731
    rain_next = lambda i: now + 30 <= i < now + 60  # noqa: E731
    wind = [55.0 if past(i) else 5.0 for i in range(hours)]
    return now, {
        "time": [(t0 + timedelta(hours=i)).strftime("%Y-%m-%dT%H:00") for i in range(hours)],
        "temperature_2m": [3.0 if rain_next(i) else -5.0 for i in range(hours)],
        "snowfall": [0.6 if past(i) else 1.0 if snow_next(i) else 0.0 for i in range(hours)],
        "rain": [0.3 if rain_next(i) else 0.0 for i in range(hours)],
        "wind_gusts_10m": [w + 20 for w in wind],
        "freezing_level_height": [1800.0] * hours,
        "snow_depth": [0.5] * hours,
        "wind_speed_850hPa": wind,
        "wind_direction_850hPa": [315.0] * hours,
    }


def test_a_summarised_point_with_every_flag_matches_the_contract():
    now, hourly = raw_series()
    p = {"id": "top", "name": {"mk": "Врв", "en": "Top"}, "lon": 21.0, "lat": 41.0, "elevation": 1500}
    now_utc = datetime.fromisoformat(hourly["time"][now]).replace(tzinfo=UTC)
    point, hours = summarise_place_point(p, {"hourly": hourly, "utc_offset_seconds": 0}, None, now_utc, [])
    assert {f["code"] for f in point["flags"]} == FLAG_CODES
    WeatherPoint.model_validate_json(json.dumps(point))
    HourlyPoint.model_validate_json(json.dumps(hours))


def test_flags_are_told_apart_by_code():
    adapter = TypeAdapter(Flag)
    flag = adapter.validate_json('{"code": "rain_on_snow", "level": "attention", "rain_mm": 6.0}')
    assert type(flag).__name__ == "RainOnSnowFlag"
    with pytest.raises(ValueError):  # a strong_wind flag needs its wind numbers
        adapter.validate_json('{"code": "strong_wind", "level": "attention", "rain_mm": 6.0}')


def test_output_that_breaks_the_contract_is_refused():
    good = json.loads((FIXTURES / "weather.json").read_text())
    checked_json(Weather, good)
    unknown_field = {**good, "surprise": 1}
    wrong_type = {**good, "places": [{**good["places"][0], "level": "extreme"}]}
    for bad in (unknown_field, wrong_type):
        with pytest.raises(ContractError):
            checked_json(Weather, bad)
