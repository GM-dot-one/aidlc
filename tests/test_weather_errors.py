"""Tests for weather error handling.

Covers the error hierarchy, the service layer's error-raising behaviour,
and the display layer's user-facing error messages.
"""

from __future__ import annotations

from io import StringIO

import pytest
from rich.console import Console

from weather.display import WeatherDisplay, format_weather_error, handle_weather_request
from weather.errors import (
    APIUnavailableError,
    CityNotFoundError,
    WeatherDataUnavailableError,
    WeatherError,
)
from weather.models import WeatherData
from weather.service import get_weather, set_api_available

# -- Exception hierarchy -----------------------------------------------------


class TestWeatherExceptions:
    def test_city_not_found_is_weather_error(self) -> None:
        assert issubclass(CityNotFoundError, WeatherError)

    def test_data_unavailable_is_weather_error(self) -> None:
        assert issubclass(WeatherDataUnavailableError, WeatherError)

    def test_api_unavailable_is_weather_error(self) -> None:
        assert issubclass(APIUnavailableError, WeatherError)

    def test_city_not_found_stores_city(self) -> None:
        err = CityNotFoundError("Atlantis")
        assert err.city == "Atlantis"
        assert "Atlantis" in str(err)

    def test_data_unavailable_stores_city_and_reason(self) -> None:
        err = WeatherDataUnavailableError("Berlin", reason="API timeout")
        assert err.city == "Berlin"
        assert err.reason == "API timeout"
        assert "Berlin" in str(err)
        assert "API timeout" in str(err)

    def test_data_unavailable_default_reason(self) -> None:
        err = WeatherDataUnavailableError("Berlin")
        assert err.reason == "no data available"

    def test_api_unavailable_stores_reason(self) -> None:
        err = APIUnavailableError("connection refused")
        assert err.reason == "connection refused"
        assert "connection refused" in str(err)

    def test_api_unavailable_default_reason(self) -> None:
        err = APIUnavailableError()
        assert err.reason == "weather service is unavailable"


# -- Service layer -----------------------------------------------------------


class TestGetWeather:
    def test_returns_data_for_known_city_with_data(self) -> None:
        result = get_weather("London")
        assert isinstance(result, WeatherData)
        assert result.city.name == "London"
        assert result.temperature_celsius == 14.0

    def test_case_insensitive_lookup(self) -> None:
        result = get_weather("PARIS")
        assert result.city.name == "Paris"

    def test_strips_whitespace(self) -> None:
        result = get_weather("  tokyo  ")
        assert result.city.name == "Tokyo"

    def test_raises_city_not_found_for_unknown_city(self) -> None:
        with pytest.raises(CityNotFoundError) as exc_info:
            get_weather("Atlantis")
        assert exc_info.value.city == "Atlantis"

    def test_raises_city_not_found_for_empty_string(self) -> None:
        with pytest.raises(CityNotFoundError):
            get_weather("")

    def test_raises_city_not_found_for_whitespace_only(self) -> None:
        with pytest.raises(CityNotFoundError):
            get_weather("   ")

    def test_raises_data_unavailable_for_known_city_without_data(self) -> None:
        with pytest.raises(WeatherDataUnavailableError) as exc_info:
            get_weather("New York")
        assert exc_info.value.city == "New York"

    def test_raises_api_unavailable_when_service_is_down(self) -> None:
        set_api_available(False)
        try:
            with pytest.raises(APIUnavailableError):
                get_weather("London")
        finally:
            set_api_available(True)

    def test_api_unavailable_takes_precedence_over_city_check(self) -> None:
        set_api_available(False)
        try:
            with pytest.raises(APIUnavailableError):
                get_weather("Atlantis")
        finally:
            set_api_available(True)


# -- Display layer -----------------------------------------------------------


class TestFormatWeatherError:
    def test_city_not_found_message(self) -> None:
        err = CityNotFoundError("Atlantis")
        msg = format_weather_error(err)
        assert "Atlantis" in msg
        assert "not found" in msg
        assert msg.startswith("Error:")

    def test_data_unavailable_message(self) -> None:
        err = WeatherDataUnavailableError("Berlin")
        msg = format_weather_error(err)
        assert "Berlin" in msg
        assert "unavailable" in msg
        assert msg.startswith("Error:")

    def test_api_unavailable_message(self) -> None:
        err = APIUnavailableError("connection refused")
        msg = format_weather_error(err)
        assert "unavailable" in msg
        assert "connection refused" in msg
        assert msg.startswith("Error:")

    def test_api_unavailable_suggests_retry(self) -> None:
        err = APIUnavailableError()
        msg = format_weather_error(err)
        assert "try again later" in msg

    def test_generic_weather_error_message(self) -> None:
        err = WeatherError("something broke")
        msg = format_weather_error(err)
        assert "unexpected" in msg
        assert "something broke" in msg


class TestHandleWeatherRequest:
    def test_success_shows_weather(self) -> None:
        result = handle_weather_request("London")
        assert "Weather for London" in result
        assert "14.0°C" in result

    def test_unknown_city_shows_error(self) -> None:
        result = handle_weather_request("Atlantis")
        assert result.startswith("Error:")
        assert "not found" in result

    def test_known_city_no_data_shows_error(self) -> None:
        result = handle_weather_request("Sydney")
        assert result.startswith("Error:")
        assert "unavailable" in result

    def test_empty_city_shows_error(self) -> None:
        result = handle_weather_request("")
        assert result.startswith("Error:")

    def test_api_unavailable_shows_error(self) -> None:
        set_api_available(False)
        try:
            result = handle_weather_request("London")
            assert result.startswith("Error:")
            assert "unavailable" in result
        finally:
            set_api_available(True)


class TestShowSummaryErrorResilience:
    def test_show_summary_completes_normally(self) -> None:
        buf = StringIO()
        console = Console(file=buf, force_terminal=True, width=120)
        display = WeatherDisplay(console)
        display.show_summary()
        output = buf.getvalue()
        assert "Weather Summary" in output

    def test_show_summary_survives_api_unavailable(self) -> None:
        buf = StringIO()
        console = Console(file=buf, force_terminal=True, width=120)
        display = WeatherDisplay(console)
        set_api_available(False)
        try:
            display.show_summary()
        finally:
            set_api_available(True)
        output = buf.getvalue()
        assert "Weather Summary" in output
