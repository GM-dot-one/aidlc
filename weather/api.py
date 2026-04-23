"""Weather data retrieval.

# TODO(ai-dlc): Task #4 (Implement weather data retrieval) should replace this
# with a real weather API integration (e.g. OpenWeatherMap, WeatherAPI).
# The current implementation returns deterministic sample data for development.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime

from weather.models import City, WeatherCondition, WeatherData

_CONDITIONS = list(WeatherCondition)


def fetch_weather(city: City) -> WeatherData:
    """Fetch weather data for a city.

    Returns deterministic sample data derived from the city name so the
    display is testable without network access.
    """
    seed = int(hashlib.md5(city.name.encode()).hexdigest()[:8], 16)
    return WeatherData(
        city=city,
        temperature_celsius=round(-10 + (seed % 4500) / 100, 1),
        humidity_percent=round(20 + (seed % 8000) / 100, 1),
        condition=_CONDITIONS[seed % len(_CONDITIONS)],
        wind_speed_kmh=round((seed % 5000) / 100, 1),
        timestamp=datetime.now(tz=UTC),
    )
