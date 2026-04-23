"""City registry for weather lookups.

Loads the curated city list from frontend/cities.json (single source of truth).
"""

from __future__ import annotations

import json
from pathlib import Path

from aidlc.weather.models import City

_CITIES_JSON = Path(__file__).resolve().parent.parent.parent / "frontend" / "cities.json"


def _load_cities() -> list[City]:
    data = json.loads(_CITIES_JSON.read_text())
    return [
        City(
            name=entry["name"],
            country=entry["country"],
            latitude=entry["lat"],
            longitude=entry["lon"],
        )
        for entry in data
    ]


_CITIES: list[City] = _load_cities()
_INDEX: dict[str, City] = {c.name.lower(): c for c in _CITIES}


class CityNotFoundError(ValueError):
    """Raised when a city name doesn't match any known city."""

    def __init__(self, city_name: str) -> None:
        super().__init__(f"City not found: {city_name!r}")
        self.city_name = city_name


def lookup_city(name: str) -> City:
    """Find a city by name (case-insensitive).

    Raises ``CityNotFoundError`` if no match is found.
    """
    city = _INDEX.get(name.strip().lower())
    if city is None:
        raise CityNotFoundError(name)
    return city


def list_cities() -> list[City]:
    """Return all available cities, sorted by name."""
    return sorted(_CITIES, key=lambda c: c.name)
