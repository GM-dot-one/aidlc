# Daily Weather Display Format

**Work Package:** #63
**Date:** 2026-04-23
**Status:** Draft

---

## Overview

This document defines the format for displaying daily weather information for a
selected city. It specifies the data fields shown, their layout, and the visual
hierarchy. The design applies to both the frontend (HTML/CSS) and the CLI
display (Rich terminal).

## Data Fields Displayed

Each daily weather display presents the following data:

| Field              | Source property          | Format / Example            | Priority |
|--------------------|--------------------------|-----------------------------|----------|
| City name          | `city.name`              | "London"                    | Required |
| Country            | `city.country`           | "UK"                        | Required |
| Temperature (°C)   | `temperature_celsius`    | "15.0 °C"                   | Required |
| Temperature (°F)   | `temperature_fahrenheit` | "59.0 °F"                   | Required |
| Weather condition   | `condition`              | "Cloudy" with icon          | Required |
| Humidity           | `humidity_percent`       | "72.5%"                     | Required |
| Wind speed         | `wind_speed_kmh`         | "12.3 km/h"                 | Required |
| Last updated       | `timestamp`              | "2026-04-23 14:30 UTC"      | Required |

## Layout — Frontend (HTML/CSS)

The daily weather display uses a card-based layout that appears when a user
clicks a city in the city list. It overlays/replaces the city metadata panel.

```
┌──────────────────────────────────────────────────┐
│  ← Back to city list                             │
├──────────────────────────────────────────────────┤
│                                                  │
│   London, UK                                     │
│   Last updated: 2026-04-23 14:30 UTC             │
│                                                  │
│  ┌──────────────────────────────────────────┐    │
│  │                                          │    │
│  │     ☁️  15.0 °C  /  59.0 °F             │    │
│  │        Cloudy                            │    │
│  │                                          │    │
│  └──────────────────────────────────────────┘    │
│                                                  │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐   │
│  │  💧        │ │  🌬️        │ │  📍        │   │
│  │  72.5%     │ │  12.3 km/h │ │  51.51°N   │   │
│  │  Humidity  │ │  Wind      │ │  0.13°W    │   │
│  └────────────┘ └────────────┘ └────────────┘   │
│                                                  │
│  Updated: 2026-04-23 14:30 UTC                   │
└──────────────────────────────────────────────────┘
```

### Visual hierarchy

1. **City name & country** — largest text, top of card (24px, semibold)
2. **Temperature** — hero element, prominent size (40px, bold), with condition
   icon to the left. Shows both °C and °F.
3. **Condition label** — directly below temperature (16px, color-coded)
4. **Detail cards** — row of three cards for humidity, wind, and coordinates
   (14px values, 12px labels)
5. **Timestamp** — bottom of the display, subdued (12px, secondary color)

### Condition color coding

| Condition      | Background gradient      | Icon |
|----------------|--------------------------|------|
| Sunny          | `#f59e0b` → `#fbbf24`   | ☀️   |
| Partly Cloudy  | `#60a5fa` → `#93c5fd`   | ⛅   |
| Cloudy         | `#9ca3af` → `#d1d5db`   | ☁️   |
| Rainy          | `#3b82f6` → `#60a5fa`   | 🌧️   |
| Stormy         | `#7c3aed` → `#a78bfa`   | ⛈️   |
| Snowy          | `#e0f2fe` → `#f0f9ff`   | ❄️   |
| Foggy          | `#d1d5db` → `#e5e7eb`   | 🌫️   |
| Windy          | `#06b6d4` → `#22d3ee`   | 💨   |

### Responsive behavior

| Breakpoint         | Layout                                          |
|--------------------|------------------------------------------------ |
| >= 600px (desktop) | Detail cards in a 3-column row                  |
| < 600px (mobile)   | Detail cards stack vertically, full width        |

## Layout — CLI (Rich Terminal)

The existing `WeatherDisplay.build_weather_panel()` in `weather/display.py`
already implements the CLI daily format as a Rich Panel with a key-value table:

```
╭──── London, UK ─────╮
│ Temperature  15.0 °C / 59.0 °F │
│ Humidity     72.5%              │
│ Condition    Cloudy             │
│ Wind         12.3 km/h         │
│ Updated      2026-04-23 14:30  │
╰─────────────────────────────────╯
```

No changes are needed to the CLI display for this work package.

## Data Source

Weather data is fetched via the `wttr.in` JSON API (`wttr.in/{city}?format=j1`),
which provides all required fields without an API key. The frontend makes a
client-side fetch call when a city card is clicked.

### wttr.in response mapping

| Display field    | wttr.in JSON path                              |
|------------------|-------------------------------------------------|
| Temperature °C   | `current_condition[0].temp_C`                  |
| Temperature °F   | `current_condition[0].temp_F`                  |
| Condition        | `current_condition[0].weatherDesc[0].value`    |
| Humidity %       | `current_condition[0].humidity`                |
| Wind km/h        | `current_condition[0].windspeedKmph`           |
| Weather icon     | Derived from `weatherCode` (mapped client-side)|

## Interaction

1. User sees the city list (existing view).
2. User clicks a city card.
3. The view transitions to the daily weather display for that city.
4. A "Back" link returns to the city list.
5. While data loads, a skeleton/loading state is shown.
6. If the API call fails, an error message with a retry button is shown.

## Accessibility

- Weather condition icons use `aria-label` attributes.
- The back button is keyboard-focusable.
- Color contrast meets WCAG 2.1 AA (4.5:1 minimum for body text).
- Temperature values include unit labels for screen readers.
