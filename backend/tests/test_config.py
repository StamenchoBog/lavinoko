"""Catch mistakes in config/regions.json before they reach the map."""

import json
from pathlib import Path

REGIONS = json.loads((Path(__file__).resolve().parents[2] / "config" / "regions.json").read_text())


def inside(lon, lat, b):
    return b[0] <= lon <= b[2] and b[1] <= lat <= b[3]


def test_place_ids_unique():
    ids = [p["id"] for p in REGIONS["places"]]
    assert len(ids) == len(set(ids))


def test_places_complete_and_inside_country():
    country = REGIONS["country"]["bounds"]
    for p in REGIONS["places"]:
        assert p["kind"] in ("resort", "touring"), p["id"]
        assert p["name"]["mk"] and p["name"]["en"] and p["range"]["mk"] and p["range"]["en"], p["id"]
        assert inside(*p["center"], country), p["id"]
        assert p["points"], p["id"]
        for pt in p["points"]:
            assert inside(pt["lon"], pt["lat"], country), (p["id"], pt["id"])
            assert 300 < pt["elevation"] < 3000, (p["id"], pt["id"])
        b = p.get("detail_bounds")
        if b:
            assert b[0] < b[2] and b[1] < b[3], p["id"]
            assert inside(*p["center"], b), p["id"]


def test_exactly_one_pilot():
    assert sum(1 for p in REGIONS["places"] if p.get("pilot")) == 1


def test_every_place_records_its_sources():
    for p in REGIONS["places"]:
        src = p.get("sources", {})
        assert src.get("location") and src.get("elevation") and src.get("checked"), p["id"]
        assert "openstreetmap" in src["location"].lower(), p["id"]
