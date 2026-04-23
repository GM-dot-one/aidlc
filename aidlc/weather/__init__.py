"""Weather data retrieval for selected cities.

Usage::

    from aidlc.weather import get_weather, list_cities

    # Get weather for a specific city
    weather = get_weather("London")
    print(f"{weather.temperature_celsius}°C, {weather.weather_description}")

    # List all available cities
    cities = list_cities()
"""

from aidlc.weather.cities import CityNotFoundError, list_cities, lookup_city
from aidlc.weather.client import WeatherAPIError, WeatherClient
from aidlc.weather.models import City, WeatherData
from aidlc.weather.retrieve import get_weather

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
