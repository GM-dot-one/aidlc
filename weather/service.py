"""Weather data retrieval with error handling.

This module wraps weather data retrieval and provides robust error handling
for cases where city data is unavailable.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from weather.cities import find_city
from weather.errors import CityNotFoundError, WeatherDataUnavailableError
from weather.models import WeatherCondition, WeatherData

# TODO(ai-dlc): Replace with real data source from task #4 (weather data retrieval).
_SAMPLE_DATA: dict[str, dict[str, Any]] = {
    "london": {
        "temperature_celsius": 14.0,
        "humidity_percent": 72.0,
        "condition": WeatherCondition.CLOUDY,
    },
    "paris": {
        "temperature_celsius": 18.5,
        "humidity_percent": 60.0,
        "condition": WeatherCondition.PARTLY_CLOUDY,
    },
    "tokyo": {
        "temperature_celsius": 22.0,
        "humidity_percent": 55.0,
        "condition": WeatherCondition.SUNNY,
    },
}

KNOWN_CITIES: set[str] = {"london", "paris", "tokyo", "new york", "sydney", "berlin"}


def _fetch_weather_data(city: str) -> dict[str, Any] | None:
    """Fetch raw weather data for a city.

    TODO(ai-dlc): Replace stub with actual API call from task #4.
    """
    return _SAMPLE_DATA.get(city.lower())


def get_weather(city: str) -> WeatherData:
    """Retrieve weather data for a city, raising descriptive errors on failure.

    Raises:
        CityNotFoundError: If the city is not recognised.
        WeatherDataUnavailableError: If the city is known but has no weather data.
    """
    if not city or not city.strip():
        raise CityNotFoundError(city)

    normalised = city.strip().lower()

    if normalised not in KNOWN_CITIES:
        raise CityNotFoundError(city)

    raw = _fetch_weather_data(normalised)
    if raw is None:
        raise WeatherDataUnavailableError(
            city, reason="weather service returned no data for this city"
        )

    city_obj = find_city(normalised)
    if city_obj is None:
        raise WeatherDataUnavailableError(city, reason="city metadata not found in registry")

    return WeatherData(
        city=city_obj,
        temperature_celsius=raw["temperature_celsius"],
        humidity_percent=raw["humidity_percent"],
        condition=raw["condition"],
        timestamp=datetime.now(tz=UTC),
    )
