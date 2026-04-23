"""City list and selection.

# TODO(ai-dlc): Task #3 (Implement city list display) should replace these
# hardcoded cities with a proper data source and interactive selection UI.
"""

from __future__ import annotations

from weather.models import City

CITIES: list[City] = [
    City(name="London", country="UK", latitude=51.5074, longitude=-0.1278),
    City(name="New York", country="US", latitude=40.7128, longitude=-74.0060),
    City(name="Tokyo", country="JP", latitude=35.6762, longitude=139.6503),
    City(name="Sydney", country="AU", latitude=-33.8688, longitude=151.2093),
    City(name="Paris", country="FR", latitude=48.8566, longitude=2.3522),
    City(name="Berlin", country="DE", latitude=52.5200, longitude=13.4050),
    City(name="Mumbai", country="IN", latitude=19.0760, longitude=72.8777),
    City(name="São Paulo", country="BR", latitude=-23.5505, longitude=-46.6333),
]


def get_cities() -> list[City]:
    return list(CITIES)


def find_city(name: str) -> City | None:
    normalized = name.strip().lower()
    return next((c for c in CITIES if c.name.lower() == normalized), None)
