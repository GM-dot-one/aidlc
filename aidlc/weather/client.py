"""Weather API client using Open-Meteo.

Open-Meteo is a free, open-source weather API that requires no API key.
https://open-meteo.com/en/docs

We fetch current conditions: temperature, humidity, wind speed, and WMO
weather code. The client follows the same httpx + tenacity pattern as
``OpenProjectClient``.
"""

from __future__ import annotations

from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from aidlc.logging import get_logger
from aidlc.weather.models import City, WeatherData

log = get_logger(__name__)

_BASE_URL = "https://api.open-meteo.com/v1/forecast"

_RETRYABLE = (httpx.TransportError, httpx.ReadTimeout, httpx.ConnectError)

# WMO Weather interpretation codes → human-readable descriptions.
# See https://open-meteo.com/en/docs#weathervariables
_WMO_CODES: dict[int, str] = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snowfall",
    73: "Moderate snowfall",
    75: "Heavy snowfall",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


class WeatherAPIError(RuntimeError):
    """Raised when the weather API returns a non-2xx response or unusable data."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class WeatherClient:
    """Thin typed client for the Open-Meteo forecast API."""

    def __init__(
        self,
        *,
        base_url: str = _BASE_URL,
        timeout: float = 10.0,
        client: httpx.Client | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._client = client or httpx.Client(timeout=timeout)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> WeatherClient:
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=8),
        retry=retry_if_exception_type(_RETRYABLE),
    )
    def _fetch(self, params: dict[str, Any]) -> dict[str, Any]:
        log.debug("weather.fetch", params=params)
        response = self._client.get(self._base_url, params=params)
        if response.status_code >= 400:
            raise WeatherAPIError(
                f"Open-Meteo {response.status_code}: {response.text[:300]}",
                status_code=response.status_code,
            )
        data: dict[str, Any] = response.json()
        return data

    def get_current_weather(self, city: City) -> WeatherData:
        """Fetch current weather conditions for a city.

        Raises ``WeatherAPIError`` if the API call fails or returns
        incomplete data.
        """
        params = {
            "latitude": city.latitude,
            "longitude": city.longitude,
            "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code",
        }
        data = self._fetch(params)

        current = data.get("current")
        if current is None:
            raise WeatherAPIError(
                f"No current weather data available for {city.name}",
            )

        weather_code = int(current.get("weather_code", -1))
        description = _WMO_CODES.get(weather_code, f"Unknown (code {weather_code})")

        return WeatherData(
            city=city,
            temperature_celsius=float(current["temperature_2m"]),
            humidity_percent=float(current["relative_humidity_2m"]),
            wind_speed_kmh=float(current["wind_speed_10m"]),
            weather_description=description,
            weather_code=weather_code,
        )


__all__ = ["WeatherAPIError", "WeatherClient"]
