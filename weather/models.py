"""Data models for the weather application."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel


class City(BaseModel):
    """A city with geographic coordinates."""

    name: str
    country: str
    latitude: float
    longitude: float

    def display_name(self) -> str:
        return f"{self.name}, {self.country}"


class WeatherCondition(StrEnum):
    SUNNY = "Sunny"
    PARTLY_CLOUDY = "Partly Cloudy"
    CLOUDY = "Cloudy"
    RAINY = "Rainy"
    STORMY = "Stormy"
    SNOWY = "Snowy"
    FOGGY = "Foggy"
    WINDY = "Windy"


class WeatherData(BaseModel):
    """Weather observation for a specific city."""

    city: City
    temperature_celsius: float
    humidity_percent: float
    condition: WeatherCondition
    wind_speed_kmh: float = 0.0
    timestamp: datetime

    @property
    def temperature_fahrenheit(self) -> float:
        return self.temperature_celsius * 9 / 5 + 32
