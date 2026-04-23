"""Custom exceptions for weather data errors."""

from __future__ import annotations


class WeatherError(Exception):
    """Base exception for all weather-related errors."""


class WeatherDataUnavailableError(WeatherError):
    """Raised when weather data cannot be retrieved for a given city."""

    def __init__(self, city: str, reason: str = "no data available") -> None:
        self.city = city
        self.reason = reason
        super().__init__(f"Weather data unavailable for '{city}': {reason}")


class CityNotFoundError(WeatherError):
    """Raised when the requested city does not exist in the data source."""

    def __init__(self, city: str) -> None:
        self.city = city
        super().__init__(f"City not found: '{city}'")
