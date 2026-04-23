"""High-level weather data retrieval.

This is the main entry point for consumers who want weather data for a city
by name. It composes the city registry and the weather API client.
"""

from __future__ import annotations

from aidlc.logging import get_logger
from aidlc.weather.cities import CityNotFoundError, list_cities, lookup_city
from aidlc.weather.client import WeatherAPIError, WeatherClient
from aidlc.weather.models import City, WeatherData

log = get_logger(__name__)


def get_weather(
    city_name: str,
    *,
    client: WeatherClient | None = None,
) -> WeatherData:
    """Retrieve current weather for a city by name.

    Parameters
    ----------
    city_name:
        Case-insensitive city name (must be in the known city list).
    client:
        Optional ``WeatherClient`` instance. If not provided, a new one is
        created and closed after use. Pass an existing client when making
        multiple calls to reuse the connection pool.

    Raises
    ------
    CityNotFoundError
        If ``city_name`` doesn't match any known city.
    WeatherAPIError
        If the weather API call fails or returns unusable data.
    """
    city = lookup_city(city_name)
    log.info("weather.retrieve", city=city.name, country=city.country)

    if client is not None:
        return client.get_current_weather(city)

    with WeatherClient() as wc:
        return wc.get_current_weather(city)


__all__ = [
    "City",
    "CityNotFoundError",
    "WeatherAPIError",
    "WeatherClient",
    "WeatherData",
    "get_weather",
    "list_cities",
    "lookup_city",
]
