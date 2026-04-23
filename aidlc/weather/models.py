"""Pydantic models for weather data retrieval."""

from __future__ import annotations

from pydantic import BaseModel


class City(BaseModel):
    """A city with geographic coordinates for weather lookups."""

    name: str
    country: str
    latitude: float
    longitude: float


class WeatherData(BaseModel):
    """Current weather conditions for a city."""

    city: City
    temperature_celsius: float
    humidity_percent: float
    wind_speed_kmh: float
    weather_description: str
    weather_code: int
