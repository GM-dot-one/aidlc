"""City registry for weather lookups.

Provides a curated set of major cities with coordinates. The city list is
intentionally small — expand it as needs grow, or replace with a geocoding
API for arbitrary city resolution.

# TODO(ai-dlc): Task #1 (Research city list and weather data sources) may
# expand this list or replace it with a dynamic geocoding lookup.
"""

from __future__ import annotations

from aidlc.weather.models import City

_CITIES: list[City] = [
    City(name="London", country="GB", latitude=51.5074, longitude=-0.1278),
    City(name="New York", country="US", latitude=40.7128, longitude=-74.0060),
    City(name="Tokyo", country="JP", latitude=35.6762, longitude=139.6503),
    City(name="Paris", country="FR", latitude=48.8566, longitude=2.3522),
    City(name="Sydney", country="AU", latitude=-33.8688, longitude=151.2093),
    City(name="Berlin", country="DE", latitude=52.5200, longitude=13.4050),
    City(name="Toronto", country="CA", latitude=43.6532, longitude=-79.3832),
    City(name="Mumbai", country="IN", latitude=19.0760, longitude=72.8777),
    City(name="São Paulo", country="BR", latitude=-23.5505, longitude=-46.6333),
    City(name="Cairo", country="EG", latitude=30.0444, longitude=31.2357),
    City(name="Dubai", country="AE", latitude=25.2048, longitude=55.2708),
    City(name="Singapore", country="SG", latitude=1.3521, longitude=103.8198),
    City(name="Los Angeles", country="US", latitude=34.0522, longitude=-118.2437),
    City(name="Beijing", country="CN", latitude=39.9042, longitude=116.4074),
    City(name="Mexico City", country="MX", latitude=19.4326, longitude=-99.1332),
    City(name="Lagos", country="NG", latitude=6.5244, longitude=3.3792),
    City(name="Seoul", country="KR", latitude=37.5665, longitude=126.9780),
    City(name="Istanbul", country="TR", latitude=41.0082, longitude=28.9784),
    City(name="Moscow", country="RU", latitude=55.7558, longitude=37.6173),
    City(name="Nairobi", country="KE", latitude=-1.2921, longitude=36.8219),
]

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
