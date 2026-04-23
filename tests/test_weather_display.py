"""Tests for the weather display module."""

from __future__ import annotations

from datetime import UTC, datetime
from io import StringIO

from rich.console import Console

from weather.api import fetch_weather
from weather.cities import find_city, get_cities
from weather.display import CONDITION_LABELS, WeatherDisplay
from weather.models import City, WeatherCondition, WeatherData


def _make_console() -> tuple[Console, StringIO]:
    buf = StringIO()
    c = Console(file=buf, force_terminal=True, width=120)
    return c, buf


def _sample_weather(
    *,
    city_name: str = "London",
    country: str = "UK",
    temp: float = 15.0,
    humidity: float = 72.5,
    condition: WeatherCondition = WeatherCondition.CLOUDY,
    wind: float = 12.3,
) -> WeatherData:
    return WeatherData(
        city=City(name=city_name, country=country, latitude=51.5, longitude=-0.1),
        temperature_celsius=temp,
        humidity_percent=humidity,
        condition=condition,
        wind_speed_kmh=wind,
        timestamp=datetime(2026, 1, 15, 12, 0, 0, tzinfo=UTC),
    )


class TestWeatherModels:
    def test_city_display_name(self) -> None:
        city = City(name="Tokyo", country="JP", latitude=35.6, longitude=139.6)
        assert city.display_name() == "Tokyo, JP"

    def test_temperature_conversion(self) -> None:
        w = _sample_weather(temp=0.0)
        assert w.temperature_fahrenheit == 32.0

        w = _sample_weather(temp=100.0)
        assert w.temperature_fahrenheit == 212.0

        w = _sample_weather(temp=-40.0)
        assert w.temperature_fahrenheit == -40.0


class TestCities:
    def test_get_cities_returns_list(self) -> None:
        cities = get_cities()
        assert len(cities) > 0
        assert all(isinstance(c, City) for c in cities)

    def test_find_city_exact(self) -> None:
        city = find_city("London")
        assert city is not None
        assert city.name == "London"

    def test_find_city_case_insensitive(self) -> None:
        city = find_city("tokyo")
        assert city is not None
        assert city.name == "Tokyo"

    def test_find_city_with_whitespace(self) -> None:
        city = find_city("  Paris  ")
        assert city is not None
        assert city.name == "Paris"

    def test_find_city_unknown(self) -> None:
        assert find_city("Atlantis") is None

    def test_get_cities_returns_copy(self) -> None:
        a = get_cities()
        b = get_cities()
        assert a is not b


class TestWeatherApi:
    def test_fetch_returns_weather_data(self) -> None:
        city = City(name="London", country="UK", latitude=51.5, longitude=-0.1)
        weather = fetch_weather(city)
        assert isinstance(weather, WeatherData)
        assert weather.city == city

    def test_fetch_is_deterministic(self) -> None:
        city = City(name="London", country="UK", latitude=51.5, longitude=-0.1)
        a = fetch_weather(city)
        b = fetch_weather(city)
        assert a.temperature_celsius == b.temperature_celsius
        assert a.humidity_percent == b.humidity_percent
        assert a.condition == b.condition

    def test_different_cities_different_weather(self) -> None:
        london = City(name="London", country="UK", latitude=51.5, longitude=-0.1)
        tokyo = City(name="Tokyo", country="JP", latitude=35.6, longitude=139.6)
        wl = fetch_weather(london)
        wt = fetch_weather(tokyo)
        assert (wl.temperature_celsius, wl.condition) != (
            wt.temperature_celsius,
            wt.condition,
        )


class TestWeatherDisplay:
    def test_build_weather_panel_contains_city_name(self) -> None:
        console, buf = _make_console()
        display = WeatherDisplay(console)
        weather = _sample_weather()
        panel = display.build_weather_panel(weather)
        console.print(panel)
        output = buf.getvalue()
        assert "London, UK" in output

    def test_build_weather_panel_contains_temperature(self) -> None:
        console, buf = _make_console()
        display = WeatherDisplay(console)
        weather = _sample_weather(temp=22.5)
        panel = display.build_weather_panel(weather)
        console.print(panel)
        output = buf.getvalue()
        assert "22.5" in output
        assert "72.5" in output

    def test_build_weather_panel_contains_humidity(self) -> None:
        console, buf = _make_console()
        display = WeatherDisplay(console)
        weather = _sample_weather(humidity=85.0)
        panel = display.build_weather_panel(weather)
        console.print(panel)
        output = buf.getvalue()
        assert "85.0%" in output

    def test_build_weather_panel_contains_fahrenheit(self) -> None:
        console, buf = _make_console()
        display = WeatherDisplay(console)
        weather = _sample_weather(temp=0.0)
        panel = display.build_weather_panel(weather)
        console.print(panel)
        output = buf.getvalue()
        assert "32.0" in output

    def test_show_renders_to_console(self) -> None:
        console, buf = _make_console()
        display = WeatherDisplay(console)
        weather = _sample_weather()
        display.show(weather)
        output = buf.getvalue()
        assert "London, UK" in output
        assert "15.0" in output

    def test_show_multiple_renders_all_cities(self) -> None:
        console, buf = _make_console()
        display = WeatherDisplay(console)
        weathers = [
            _sample_weather(city_name="London", country="UK"),
            _sample_weather(city_name="Tokyo", country="JP"),
        ]
        display.show_multiple(weathers)
        output = buf.getvalue()
        assert "London, UK" in output
        assert "Tokyo, JP" in output

    def test_show_multiple_empty_list(self) -> None:
        console, buf = _make_console()
        display = WeatherDisplay(console)
        display.show_multiple([])
        output = buf.getvalue()
        assert "No weather data" in output

    def test_show_city_list(self) -> None:
        console, buf = _make_console()
        display = WeatherDisplay(console)
        cities = get_cities()
        display.show_city_list(cities)
        output = buf.getvalue()
        assert "London" in output
        assert "Tokyo" in output
        assert "Available Cities" in output

    def test_show_summary(self) -> None:
        console, buf = _make_console()
        display = WeatherDisplay(console)
        display.show_summary()
        output = buf.getvalue()
        assert "Weather Summary" in output
        for city in get_cities():
            assert city.name in output

    def test_condition_labels_cover_all_conditions(self) -> None:
        for condition in WeatherCondition:
            assert condition in CONDITION_LABELS

    def test_display_updates_on_city_change(self) -> None:
        """Verify that the display shows different data when the city changes."""
        console, buf = _make_console()
        display = WeatherDisplay(console)

        london = find_city("London")
        assert london is not None
        london_weather = fetch_weather(london)
        display.show(london_weather)
        london_output = buf.getvalue()

        buf.truncate(0)
        buf.seek(0)

        tokyo = find_city("Tokyo")
        assert tokyo is not None
        tokyo_weather = fetch_weather(tokyo)
        display.show(tokyo_weather)
        tokyo_output = buf.getvalue()

        assert "London, UK" in london_output
        assert "Tokyo, JP" in tokyo_output
        assert "London" not in tokyo_output
