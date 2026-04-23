"""Custom exceptions for weather data errors."""

from __future__ import annotations


class WeatherError(Exception):
    """Base exception for all weather-related errors."""


class CityNotFoundError(WeatherError):
    """Raised when the requested city does not exist in the data source."""

    def __init__(self, city: str) -> None:
        self.city = city
        super().__init__(f"City not found: '{city}'")


class WeatherDataUnavailableError(WeatherError):
    """Raised when weather data cannot be retrieved for a given city."""

    def __init__(self, city: str, reason: str = "no data available") -> None:
        self.city = city
        self.reason = reason
        super().__init__(f"Weather data unavailable for '{city}': {reason}")


class APIUnavailableError(WeatherError):
    """Raised when the weather API is unreachable or returns a server error."""

    def __init__(self, reason: str = "weather service is unavailable") -> None:
        self.reason = reason
        super().__init__(f"API unavailable: {reason}")
