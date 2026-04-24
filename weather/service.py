"""Weather data retrieval with error handling.

This module wraps weather data retrieval and provides robust error handling
for cases where city data is unavailable.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from weather.cities import find_city
from weather.errors import (
    APIUnavailableError,
    CityNotFoundError,
    WeatherDataUnavailableError,
)
from weather.models import WeatherCondition, WeatherData

_SAMPLE_DATA: dict[str, dict[str, Any]] = {
    "london": {
        "temperature_celsius": 14.0,
        "humidity_percent": 72.0,
        "condition": WeatherCondition.CLOUDY,
        "wind_speed_kmh": 15.0,
    },
    "paris": {
        "temperature_celsius": 18.5,
        "humidity_percent": 60.0,
        "condition": WeatherCondition.PARTLY_CLOUDY,
        "wind_speed_kmh": 10.0,
    },
    "tokyo": {
        "temperature_celsius": 22.0,
        "humidity_percent": 55.0,
        "condition": WeatherCondition.SUNNY,
        "wind_speed_kmh": 8.0,
    },
}

KNOWN_CITIES: set[str] = {"london", "paris", "tokyo", "new york", "sydney", "berlin"}

_api_available: bool = True


def set_api_available(available: bool) -> None:
    """Control simulated API availability (for testing)."""
    global _api_available
    _api_available = available


def get_weather(city: str) -> WeatherData:
    """Retrieve weather data for a city, raising descriptive errors on failure.

    Raises:
        CityNotFoundError: If the city is not recognised.
        WeatherDataUnavailableError: If the city is known but has no weather data.
        APIUnavailableError: If the weather service is unreachable.
    """
    if not _api_available:
        raise APIUnavailableError("weather service is unavailable")

    if not city or not city.strip():
        raise CityNotFoundError(city)

    normalised = city.strip().lower()

    if normalised not in KNOWN_CITIES:
        raise CityNotFoundError(city)

    raw = _SAMPLE_DATA.get(normalised)
    if raw is None:
        raise WeatherDataUnavailableError(
            city, reason="weather service returned no data for this city"
        )

    city_obj = find_city(city)
    if city_obj is None:
        raise WeatherDataUnavailableError(city, reason="city coordinates unavailable")

    return WeatherData(
        city=city_obj,
        temperature_celsius=raw["temperature_celsius"],
        humidity_percent=raw["humidity_percent"],
        condition=raw["condition"],
        wind_speed_kmh=raw.get("wind_speed_kmh", 0.0),
        timestamp=datetime.now(tz=UTC),
    )
