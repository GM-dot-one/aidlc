"""CLI entry point for the weather display application."""

from __future__ import annotations

from typing import Annotated

import typer
from rich.console import Console

from weather.api import fetch_weather
from weather.cities import find_city, get_cities
from weather.display import WeatherDisplay

app = typer.Typer(
    no_args_is_help=True,
    add_completion=False,
    help="Weather display — view temperature, humidity, and conditions for cities worldwide.",
)
console = Console()


@app.command()
def show(
    city_name: Annotated[
        str | None,
        typer.Argument(help="City name to display weather for"),
    ] = None,
) -> None:
    """Show weather for a specific city, or all cities if none specified."""
    display = WeatherDisplay(console)

    if city_name is None:
        display.show_summary()
        return

    city = find_city(city_name)
    if city is None:
        console.print(f"[red]Unknown city:[/] {city_name!r}")
        console.print("Available cities:")
        for c in get_cities():
            console.print(f"  - {c.display_name()}")
        raise typer.Exit(code=1)

    weather = fetch_weather(city)
    display.show(weather)


@app.command()
def interactive() -> None:
    """Launch an interactive session — select cities and view weather."""
    display = WeatherDisplay(console)
    display.run_interactive()


@app.command()
def cities() -> None:
    """List all available cities."""
    display = WeatherDisplay(console)
    display.show_city_list(get_cities())


if __name__ == "__main__":
    app()
