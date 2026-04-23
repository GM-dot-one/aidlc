"""Tests for the weather data retrieval module."""

from __future__ import annotations

import httpx
import pytest
import respx

from aidlc.weather import (
    WeatherClient,
)
from aidlc.weather.cities import CityNotFoundError, list_cities, lookup_city
from aidlc.weather.client import WeatherAPIError
from aidlc.weather.models import City
from aidlc.weather.retrieve import get_weather

API_BASE = "https://api.open-meteo.com/v1/forecast"

_SAMPLE_RESPONSE = {
    "current": {
        "temperature_2m": 18.5,
        "relative_humidity_2m": 65.0,
        "wind_speed_10m": 12.3,
        "weather_code": 2,
    }
}


# ---- City lookup -----------------------------------------------------------


def test_lookup_city_returns_matching_city() -> None:
    city = lookup_city("London")
    assert city.name == "London"
    assert city.country == "GB"
    assert city.latitude == pytest.approx(51.5074)


def test_lookup_city_is_case_insensitive() -> None:
    assert lookup_city("london").name == "London"
    assert lookup_city("TOKYO").name == "Tokyo"
    assert lookup_city("  Paris  ").name == "Paris"


def test_lookup_city_raises_for_unknown() -> None:
    with pytest.raises(CityNotFoundError) as exc_info:
        lookup_city("Atlantis")
    assert "Atlantis" in str(exc_info.value)
    assert exc_info.value.city_name == "Atlantis"


def test_list_cities_returns_sorted_list() -> None:
    cities = list_cities()
    assert len(cities) > 0
    names = [c.name for c in cities]
    assert names == sorted(names)


# ---- WeatherClient --------------------------------------------------------


@respx.mock
def test_get_current_weather_parses_response() -> None:
    respx.get(API_BASE).mock(return_value=httpx.Response(200, json=_SAMPLE_RESPONSE))
    city = City(name="London", country="GB", latitude=51.5074, longitude=-0.1278)
    with WeatherClient() as wc:
        result = wc.get_current_weather(city)

    assert result.city.name == "London"
    assert result.temperature_celsius == pytest.approx(18.5)
    assert result.humidity_percent == pytest.approx(65.0)
    assert result.wind_speed_kmh == pytest.approx(12.3)
    assert result.weather_code == 2
    assert result.weather_description == "Partly cloudy"


@respx.mock
def test_get_current_weather_raises_on_4xx() -> None:
    respx.get(API_BASE).mock(return_value=httpx.Response(400, text='{"reason":"bad request"}'))
    city = City(name="Test", country="XX", latitude=0.0, longitude=0.0)
    with WeatherClient() as wc, pytest.raises(WeatherAPIError) as exc_info:
        wc.get_current_weather(city)
    assert exc_info.value.status_code == 400


@respx.mock
def test_get_current_weather_raises_on_missing_current_block() -> None:
    respx.get(API_BASE).mock(
        return_value=httpx.Response(200, json={"latitude": 51.5, "longitude": -0.1})
    )
    city = City(name="London", country="GB", latitude=51.5074, longitude=-0.1278)
    with WeatherClient() as wc, pytest.raises(WeatherAPIError, match="No current weather"):
        wc.get_current_weather(city)


@respx.mock
def test_unknown_weather_code_produces_fallback_description() -> None:
    response_data = {
        "current": {
            "temperature_2m": 20.0,
            "relative_humidity_2m": 50.0,
            "wind_speed_10m": 5.0,
            "weather_code": 999,
        }
    }
    respx.get(API_BASE).mock(return_value=httpx.Response(200, json=response_data))
    city = City(name="Test", country="XX", latitude=0.0, longitude=0.0)
    with WeatherClient() as wc:
        result = wc.get_current_weather(city)
    assert "Unknown" in result.weather_description


@respx.mock
def test_client_sends_correct_query_params() -> None:
    route = respx.get(API_BASE).mock(return_value=httpx.Response(200, json=_SAMPLE_RESPONSE))
    city = City(name="Tokyo", country="JP", latitude=35.6762, longitude=139.6503)
    with WeatherClient() as wc:
        wc.get_current_weather(city)

    request = route.calls[0].request
    assert "latitude=35.6762" in str(request.url)
    assert "longitude=139.6503" in str(request.url)
    assert "temperature_2m" in str(request.url)


# ---- High-level get_weather ------------------------------------------------


@respx.mock
def test_get_weather_happy_path() -> None:
    respx.get(API_BASE).mock(return_value=httpx.Response(200, json=_SAMPLE_RESPONSE))
    result = get_weather("London")
    assert result.city.name == "London"
    assert result.temperature_celsius == pytest.approx(18.5)


@respx.mock
def test_get_weather_with_injected_client() -> None:
    respx.get(API_BASE).mock(return_value=httpx.Response(200, json=_SAMPLE_RESPONSE))
    with WeatherClient() as wc:
        result = get_weather("Paris", client=wc)
    assert result.city.name == "Paris"


def test_get_weather_raises_for_unknown_city() -> None:
    with pytest.raises(CityNotFoundError):
        get_weather("Atlantis")


@respx.mock
def test_get_weather_propagates_api_errors() -> None:
    respx.get(API_BASE).mock(return_value=httpx.Response(500, text="internal error"))
    with pytest.raises(WeatherAPIError):
        get_weather("Berlin")
