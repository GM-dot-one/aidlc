# Weather Application — UI Design Specification

**Work Package:** #50
**Status:** Draft

---

## Overview

This document describes the user interface design for the weather application.
The app lets users browse a list of cities and view current weather conditions
for each selected city. An interactive HTML wireframe is provided alongside this
spec (see `docs/wireframes/weather-app.html`).

## Screen Layout

The application uses a **two-panel layout**:

```
┌──────────────────────────────────────────────────────────────────────┐
│  [logo]  Weather App                              [search] [settings]│
├──────────────────┬───────────────────────────────────────────────────┤
│                  │                                                   │
│  CITY LIST       │  WEATHER DISPLAY                                  │
│  ────────────    │  ────────────────                                 │
│                  │                                                   │
│  [+] Add City    │   ┌──────────────────────────────┐               │
│                  │   │  City Name, Country           │               │
│  ┌────────────┐  │   │  Last updated: 2 min ago      │               │
│  │ > London   │  │   ├──────────────────────────────┤               │
│  │   12°C     │  │   │                              │               │
│  │   Cloudy   │  │   │   ☀  24°C                   │               │
│  ├────────────┤  │   │   Partly Cloudy              │               │
│  │   Paris    │  │   │   Feels like 22°C            │               │
│  │   18°C     │  │   │                              │               │
│  │   Sunny    │  │   ├──────────────────────────────┤               │
│  ├────────────┤  │   │ Humidity │ Wind  │ Pressure  │               │
│  │   Tokyo    │  │   │   65%    │ 12kph │ 1013 hPa  │               │
│  │   22°C     │  │   ├──────────────────────────────┤               │
│  ├────────────┤  │   │                              │               │
│  │   New York │  │   │  5-Day Forecast              │               │
│  │   15°C     │  │   │  Mon  Tue  Wed  Thu  Fri     │               │
│  │   Rain     │  │   │  18°  20°  22°  19°  17°     │               │
│  └────────────┘  │   │  ☁   ☀   ☀   🌧  ☁        │               │
│                  │   └──────────────────────────────┘               │
│                  │                                                   │
└──────────────────┴───────────────────────────────────────────────────┘
```

## Components

### 1. Header Bar

| Element     | Description                                                |
|-------------|------------------------------------------------------------|
| Logo / Title| App name "Weather App" with a sun/cloud icon.              |
| Search      | Text input to filter or search for cities by name.         |
| Settings    | Gear icon opening a dropdown for unit toggle (°C / °F).    |

### 2. City List Panel (Left — ~280 px wide)

- Vertical scrollable list of saved cities.
- Each city card shows: **city name**, **current temperature**, **short condition** (e.g. "Cloudy").
- The **selected city** is visually highlighted (accent background + left border).
- An **"Add City"** button at the top opens a search/autocomplete dialog.
- Cities can be **removed** via a hover-revealed delete icon on each card.

**Interactions:**
- Click a city card to select it and update the right panel.
- Drag-and-drop to reorder (stretch goal).
- Swipe-to-delete on mobile (stretch goal).

### 3. Weather Display Panel (Right — fills remaining space)

#### 3a. Current Conditions

- **City name and country** in a large heading.
- **Last updated** timestamp.
- **Weather icon** (large, illustrative) + **temperature** (prominent, ~48 px font).
- **Condition label** (e.g. "Partly Cloudy").
- **Feels-like temperature**.

#### 3b. Detail Row

A horizontal row of three cards:

| Card     | Content               |
|----------|-----------------------|
| Humidity | Percentage + icon     |
| Wind     | Speed + direction     |
| Pressure | hPa / inHg + icon    |

#### 3c. 5-Day Forecast

- Horizontal row of day columns.
- Each column: **day label**, **icon**, **high / low temperature**.

### 4. Empty / Loading / Error States

| State        | Behavior                                                      |
|--------------|---------------------------------------------------------------|
| No cities    | Center prompt: "Add a city to get started" with CTA button.   |
| Loading      | Skeleton placeholders on city cards and weather panel.         |
| API error    | Inline banner at top of weather panel with retry button.       |
| City not found | Toast notification when search yields no results.           |

## Responsive Behavior

| Breakpoint       | Layout                                                  |
|------------------|---------------------------------------------------------|
| >= 768 px (desktop/tablet) | Side-by-side two-panel layout.                |
| < 768 px (mobile)          | Stacked: city list on top, tap to expand weather detail below. Back arrow to return to list. |

## Color Palette

| Token              | Value       | Usage                        |
|--------------------|-------------|------------------------------|
| `--bg-primary`     | `#f0f4f8`   | Page background              |
| `--bg-card`        | `#ffffff`   | Card surfaces                |
| `--accent`         | `#3b82f6`   | Selected state, buttons      |
| `--text-primary`   | `#1e293b`   | Headings, primary text       |
| `--text-secondary` | `#64748b`   | Metadata, secondary labels   |
| `--danger`         | `#ef4444`   | Delete action, error states  |

## Typography

- **Font family:** System font stack (`-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`).
- **Temperature (hero):** 48 px, bold.
- **City name in panel:** 24 px, semibold.
- **Card labels:** 14 px, regular.
- **Metadata:** 12 px, secondary color.

## Accessibility

- All interactive elements are keyboard-navigable.
- Color contrast ratios meet WCAG 2.1 AA (minimum 4.5:1 for body text).
- Weather icons include `aria-label` descriptions.
- The city list supports `role="listbox"` with `aria-selected` on the active item.
- Unit toggle persists via `localStorage` and is announced to screen readers.

## Open Questions

- **Data source:** Which weather API will be used? (OpenWeatherMap, WeatherAPI, etc.)
- **Authentication:** Will users have accounts, or is the city list stored locally?
- **Hourly forecast:** Should we include an hourly breakdown in addition to 5-day?
