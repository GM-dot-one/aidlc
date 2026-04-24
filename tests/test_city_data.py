"""Validate the city list data file used by the frontend."""

from __future__ import annotations

import json
from pathlib import Path

CITIES_JSON = Path(__file__).resolve().parent.parent / "frontend" / "cities.json"

REQUIRED_KEYS = {"id", "name", "country", "population", "lat", "lon", "wttr_query"}


def test_cities_json_exists():
    assert CITIES_JSON.is_file(), f"{CITIES_JSON} not found"


def test_cities_json_is_valid():
    data = json.loads(CITIES_JSON.read_text())
    assert isinstance(data, list)
    assert len(data) > 0


def test_each_city_has_required_fields():
    data = json.loads(CITIES_JSON.read_text())
    for i, city in enumerate(data):
        missing = REQUIRED_KEYS - set(city.keys())
        assert not missing, f"City at index {i} ({city.get('name', '?')}) missing keys: {missing}"


def test_field_types():
    data = json.loads(CITIES_JSON.read_text())
    for city in data:
        assert isinstance(city["name"], str) and city["name"]
        assert isinstance(city["country"], str) and city["country"]
        assert isinstance(city["population"], int) and city["population"] > 0
        assert isinstance(city["lat"], (int, float)) and -90 <= city["lat"] <= 90
        assert isinstance(city["lon"], (int, float)) and -180 <= city["lon"] <= 180


def test_no_duplicate_cities():
    data = json.loads(CITIES_JSON.read_text())
    names = [c["name"] for c in data]
    assert len(names) == len(set(names)), "Duplicate city names found"


def test_no_duplicate_ids():
    data = json.loads(CITIES_JSON.read_text())
    ids = [c["id"] for c in data]
    assert len(ids) == len(set(ids)), "Duplicate city IDs found"


def test_id_format():
    data = json.loads(CITIES_JSON.read_text())
    import re

    for city in data:
        assert re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", city["id"]), (
            f"City ID {city['id']!r} is not a valid lowercase hyphenated slug"
        )


def test_wttr_query_is_nonempty_string():
    data = json.loads(CITIES_JSON.read_text())
    for city in data:
        assert isinstance(city["wttr_query"], str) and city["wttr_query"], (
            f"City {city['name']} has invalid wttr_query"
        )


def test_geographic_diversity():
    data = json.loads(CITIES_JSON.read_text())
    has_northern = any(c["lat"] > 23.5 for c in data)
    has_southern = any(c["lat"] < -23.5 for c in data)
    has_eastern = any(c["lon"] > 100 for c in data)
    has_western = any(c["lon"] < -50 for c in data)
    assert has_northern, "No cities in northern latitudes"
    assert has_southern, "No cities in southern latitudes"
    assert has_eastern, "No cities in eastern longitudes"
    assert has_western, "No cities in western longitudes"


def test_sorted_by_name():
    data = json.loads(CITIES_JSON.read_text())
    names = [c["name"] for c in data]
    assert names == sorted(names), "Cities should be sorted alphabetically by name"
