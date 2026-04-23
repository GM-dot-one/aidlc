"""Validate the city list data file used by the frontend."""

from __future__ import annotations

import json
from pathlib import Path

CITIES_JSON = Path(__file__).resolve().parent.parent / "frontend" / "cities.json"

REQUIRED_KEYS = {"name", "country", "population", "lat", "lon"}


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
