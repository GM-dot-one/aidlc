"""Weather display — renders weather data in the terminal using rich.

This is the core of task #53: display temperature, humidity, and weather
conditions, updating when the user selects a different city.
"""

from __future__ import annotations

from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from weather.api import fetch_weather
from weather.cities import find_city, get_cities
from weather.models import City, WeatherCondition, WeatherData

CONDITION_LABELS: dict[WeatherCondition, str] = {
    WeatherCondition.SUNNY: "[yellow]Sunny[/]",
    WeatherCondition.PARTLY_CLOUDY: "[yellow]Partly Cloudy[/]",
    WeatherCondition.CLOUDY: "[dim]Cloudy[/]",
    WeatherCondition.RAINY: "[blue]Rainy[/]",
    WeatherCondition.STORMY: "[bold red]Stormy[/]",
    WeatherCondition.SNOWY: "[white]Snowy[/]",
    WeatherCondition.FOGGY: "[dim]Foggy[/]",
    WeatherCondition.WINDY: "[cyan]Windy[/]",
}


class WeatherDisplay:
    """Renders weather information to the terminal."""

    def __init__(self, console: Console | None = None) -> None:
        self.console = console or Console()

    def build_weather_panel(self, weather: WeatherData) -> Panel:
        """Build a rich Panel showing weather details for one city."""
        condition_label = CONDITION_LABELS.get(weather.condition, str(weather.condition.value))

        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column("label", style="bold", min_width=14)
        table.add_column("value")

        table.add_row(
            "Temperature",
            f"{weather.temperature_celsius:.1f} °C  /  {weather.temperature_fahrenheit:.1f} °F",
        )
        table.add_row("Humidity", f"{weather.humidity_percent:.1f}%")
        table.add_row("Condition", condition_label)
        table.add_row("Wind", f"{weather.wind_speed_kmh:.1f} km/h")
        table.add_row(
            "Updated",
            weather.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC"),
        )

        return Panel(
            table,
            title=f"[bold]{weather.city.display_name()}[/]",
            border_style="blue",
            expand=False,
        )

    def show(self, weather: WeatherData) -> None:
        """Render a single city's weather to the console."""
        self.console.print()
        self.console.print(self.build_weather_panel(weather))

    def show_multiple(self, weather_list: list[WeatherData]) -> None:
        """Render weather panels for multiple cities side by side."""
        if not weather_list:
            self.console.print("[dim]No weather data to display.[/]")
            return
        panels = [self.build_weather_panel(w) for w in weather_list]
        self.console.print()
        self.console.print(Columns(panels, equal=True, expand=True))

    def show_city_list(self, cities: list[City], header: str = "Available Cities") -> None:
        """Display a numbered list of cities."""
        table = Table(title=header, show_lines=False)
        table.add_column("#", style="dim", width=4)
        table.add_column("City", style="bold")
        table.add_column("Country")
        table.add_column("Coordinates", style="dim")

        for i, city in enumerate(cities, 1):
            table.add_row(
                str(i),
                city.name,
                city.country,
                f"{city.latitude:.2f}, {city.longitude:.2f}",
            )

        self.console.print()
        self.console.print(table)

    def prompt_city_selection(self, cities: list[City]) -> City | None:
        """Prompt the user to select a city by number or name.

        Returns None if the input doesn't match any city.
        """
        self.show_city_list(cities)
        self.console.print()
        choice = self.console.input("[bold]Select a city[/] (number or name): ").strip()

        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(cities):
                return cities[idx]
            return None

        return find_city(choice)

    def run_interactive(self) -> None:
        """Run an interactive loop: select a city, view weather, repeat."""
        cities = get_cities()
        self.console.print(
            Panel(
                "[bold]Weather Display[/]\n"
                "Select a city to view current weather conditions.\n"
                "Type [bold]q[/] to quit.",
                border_style="green",
            )
        )

        while True:
            self.show_city_list(cities)
            self.console.print()
            choice = self.console.input(
                "[bold]Select a city[/] (number, name, or [bold]q[/] to quit): "
            ).strip()

            if choice.lower() in ("q", "quit", "exit"):
                self.console.print("[dim]Goodbye.[/]")
                break

            city: City | None = None
            if choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(cities):
                    city = cities[idx]
            else:
                city = find_city(choice)

            if city is None:
                self.console.print(f"[red]Unknown city:[/] {choice!r}. Try again.")
                continue

            weather = fetch_weather(city)
            self.show(weather)

    def show_summary(self) -> None:
        """Fetch and display weather for all cities at once."""
        cities = get_cities()
        weather_list = [fetch_weather(c) for c in cities]
        self.console.print(
            Text("Weather Summary", style="bold underline"),
            justify="center",
        )
        self.show_multiple(weather_list)
