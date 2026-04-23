# Research: Free Weather APIs

**Work Package:** #61
**Date:** 2026-04-23
**Status:** Complete

---

## Objective

Evaluate free weather APIs for integration into the City List application, a single-page HTML/CSS/vanilla JavaScript app with no server or build tools. The chosen API must be callable directly from browser JavaScript (CORS support, ideally no API key).

---

## Candidates Evaluated

### 1. wttr.in

| Attribute            | Detail                                               |
|----------------------|------------------------------------------------------|
| **Base URL**         | `https://wttr.in`                                    |
| **API key required** | No                                                   |
| **CORS support**     | Yes                                                  |
| **Rate limits**      | Undocumented; fair-use policy (no hard published cap) |
| **Cost**             | Free for all use                                     |
| **License**          | Open-source (Apache 2.0)                             |
| **Data source**      | Aggregates from WorldWeatherOnline and others        |

#### Endpoints

**Current weather + 3-day forecast (JSON)**

```
GET https://wttr.in/{location}?format=j1
```

| Parameter   | Type   | Description                                                      |
|-------------|--------|------------------------------------------------------------------|
| `{location}`| path   | City name (e.g., `London`), lat/lon (e.g., `48.8566,2.3522`), airport code, or IP address |
| `format`    | query  | `j1` for JSON output (compact), `j2` for extended JSON          |
| `lang`      | query  | Language code (e.g., `en`, `fr`, `de`)                           |
| `m`         | query  | Metric units (default)                                           |
| `u`         | query  | USCS/imperial units                                              |
| `M`         | query  | Wind speed in m/s                                                |

**Example request:**
```
GET https://wttr.in/London?format=j1
```

**Response format (`j1`):**

```json
{
  "current_condition": [
    {
      "temp_C": "15",
      "temp_F": "59",
      "humidity": "72",
      "weatherDesc": [{"value": "Partly cloudy"}],
      "weatherCode": "116",
      "windspeedKmph": "19",
      "windspeedMiles": "12",
      "winddirDegree": "230",
      "winddir16Point": "SW",
      "precipMM": "0.0",
      "pressure": "1015",
      "pressureInches": "30",
      "visibility": "10",
      "visibilityMiles": "6",
      "cloudcover": "50",
      "FeelsLikeC": "13",
      "FeelsLikeF": "55",
      "uvIndex": "4",
      "observation_time": "02:00 PM"
    }
  ],
  "nearest_area": [
    {
      "areaName": [{"value": "London"}],
      "country": [{"value": "United Kingdom"}],
      "latitude": "51.517",
      "longitude": "-0.106",
      "population": "7556900"
    }
  ],
  "weather": [
    {
      "date": "2026-04-23",
      "mintempC": "8",
      "maxtempC": "17",
      "mintempF": "46",
      "maxtempF": "63",
      "avgtempC": "13",
      "avgtempF": "55",
      "totalSnow_cm": "0.0",
      "sunHour": "7.2",
      "uvIndex": "4",
      "hourly": [
        {
          "time": "0",
          "tempC": "10",
          "tempF": "50",
          "weatherDesc": [{"value": "Clear"}],
          "weatherCode": "113",
          "windspeedKmph": "11",
          "humidity": "80",
          "precipMM": "0.0",
          "chanceofrain": "0"
        }
      ]
    }
  ]
}
```

**Key response fields:**

| Path                                | Type   | Description                    |
|-------------------------------------|--------|--------------------------------|
| `current_condition[0].temp_C`       | string | Current temperature in Celsius |
| `current_condition[0].temp_F`       | string | Current temperature in Fahrenheit |
| `current_condition[0].humidity`     | string | Relative humidity (%)          |
| `current_condition[0].weatherDesc[0].value` | string | Human-readable description |
| `current_condition[0].weatherCode`  | string | Numeric weather condition code |
| `current_condition[0].windspeedKmph`| string | Wind speed in km/h             |
| `current_condition[0].FeelsLikeC`   | string | Feels-like temperature (C)     |
| `weather[].date`                    | string | Forecast date (YYYY-MM-DD)     |
| `weather[].mintempC` / `maxtempC`   | string | Daily min/max temperature (C)  |
| `weather[].hourly[]`               | array  | Hourly breakdown (8 entries/day)|

**Notes:**
- All numeric values are returned as **strings**, not numbers; parse them in JS.
- The `weather` array contains 3 days of forecast data (today + 2 days).
- Each day's `hourly` array has 8 entries (every 3 hours).
- Supports lat/lon lookup: `https://wttr.in/48.8566,2.3522?format=j1`.

---

### 2. OpenWeatherMap

| Attribute            | Detail                                               |
|----------------------|------------------------------------------------------|
| **Base URL**         | `https://api.openweathermap.org`                     |
| **API key required** | Yes (`appid` query parameter)                        |
| **CORS support**     | Yes                                                  |
| **Rate limits**      | Free tier: 60 calls/min, 1,000 calls/day             |
| **Cost**             | Free tier available; paid from ~$0/month              |
| **License**          | Proprietary                                          |
| **Data source**      | Proprietary blend of global weather stations, satellites, radar |

#### Endpoints

**Current weather**

```
GET https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={API_KEY}&units=metric
```

| Parameter | Type  | Description                                                   |
|-----------|-------|---------------------------------------------------------------|
| `lat`     | query | Latitude                                                      |
| `lon`     | query | Longitude                                                     |
| `q`       | query | City name (alternative to lat/lon), e.g., `q=London`          |
| `appid`   | query | **Required.** API key from openweathermap.org                 |
| `units`   | query | `metric` (Celsius), `imperial` (Fahrenheit), `standard` (Kelvin, default) |
| `lang`    | query | Language code for descriptions                                |

**Example request:**
```
GET https://api.openweathermap.org/data/2.5/weather?lat=51.5074&lon=-0.1278&appid=YOUR_KEY&units=metric
```

**Response format:**

```json
{
  "coord": {"lon": -0.1278, "lat": 51.5074},
  "weather": [
    {
      "id": 802,
      "main": "Clouds",
      "description": "scattered clouds",
      "icon": "03d"
    }
  ],
  "main": {
    "temp": 15.2,
    "feels_like": 13.1,
    "temp_min": 13.0,
    "temp_max": 17.0,
    "pressure": 1015,
    "humidity": 72
  },
  "visibility": 10000,
  "wind": {"speed": 5.14, "deg": 230, "gust": 8.2},
  "clouds": {"all": 40},
  "dt": 1745424000,
  "sys": {"country": "GB", "sunrise": 1745383200, "sunset": 1745434800},
  "timezone": 3600,
  "name": "London"
}
```

**5-day / 3-hour forecast (free tier)**

```
GET https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={API_KEY}&units=metric
```

Parameters are the same as the current weather endpoint. Response contains a `list` array of 40 entries (every 3 hours for 5 days), each with the same structure as the current weather `main`, `weather`, `wind`, etc.

**Weather icons:**
```
https://openweathermap.org/img/wn/{icon}@2x.png
```
Where `{icon}` is from `weather[0].icon` (e.g., `03d`).

**Notes:**
- Returns numeric types (not strings) for temperature, wind, etc.
- API key is **required** and would be **exposed in client-side JS** (no server to proxy through).
- Free tier allows commercial use.
- New API keys can take up to 2 hours to activate after registration.

---

### 3. Open-Meteo

| Attribute            | Detail                                               |
|----------------------|------------------------------------------------------|
| **Base URL**         | `https://api.open-meteo.com`                         |
| **API key required** | No                                                   |
| **CORS support**     | Yes                                                  |
| **Rate limits**      | 10,000 requests/day (free, non-commercial)           |
| **Cost**             | Free (non-commercial); from EUR 15/month (commercial)|
| **License**          | CC BY 4.0 for data; API is open                      |
| **Data source**      | Aggregates DWD, NOAA, MeteoFrance, and others        |

#### Endpoints

**Forecast (current + up to 16 days)**

```
GET https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true&daily=temperature_2m_max,temperature_2m_min,weathercode&timezone=auto
```

| Parameter          | Type  | Description                                                    |
|--------------------|-------|----------------------------------------------------------------|
| `latitude`         | query | Latitude                                                       |
| `longitude`        | query | Longitude                                                      |
| `current_weather`  | query | `true` to include current conditions                           |
| `hourly`           | query | Comma-separated list of hourly variables (e.g., `temperature_2m,relativehumidity_2m`) |
| `daily`            | query | Comma-separated list of daily variables (e.g., `temperature_2m_max,temperature_2m_min`) |
| `timezone`         | query | `auto` to match location, or IANA timezone string              |
| `forecast_days`    | query | Number of forecast days (1-16, default 7)                      |
| `temperature_unit` | query | `celsius` (default) or `fahrenheit`                            |
| `windspeed_unit`   | query | `kmh` (default), `ms`, `mph`, `kn`                            |

**Example request:**
```
GET https://api.open-meteo.com/v1/forecast?latitude=51.5074&longitude=-0.1278&current_weather=true&daily=temperature_2m_max,temperature_2m_min,weathercode&timezone=auto
```

**Response format:**

```json
{
  "latitude": 51.5,
  "longitude": -0.12,
  "generationtime_ms": 0.5,
  "utc_offset_seconds": 3600,
  "timezone": "Europe/London",
  "current_weather": {
    "temperature": 15.2,
    "windspeed": 18.7,
    "winddirection": 230,
    "weathercode": 2,
    "is_day": 1,
    "time": "2026-04-23T14:00"
  },
  "daily": {
    "time": ["2026-04-23", "2026-04-24", "2026-04-25"],
    "temperature_2m_max": [17.0, 16.5, 18.2],
    "temperature_2m_min": [8.0, 7.5, 9.1],
    "weathercode": [2, 3, 1]
  },
  "daily_units": {
    "temperature_2m_max": "°C",
    "temperature_2m_min": "°C"
  }
}
```

**WMO Weather Codes** (used in `weathercode`):

| Code | Description          |
|------|----------------------|
| 0    | Clear sky            |
| 1    | Mainly clear         |
| 2    | Partly cloudy        |
| 3    | Overcast             |
| 45   | Fog                  |
| 51   | Light drizzle        |
| 61   | Slight rain          |
| 63   | Moderate rain        |
| 65   | Heavy rain           |
| 71   | Slight snow fall     |
| 80   | Slight rain showers  |
| 95   | Thunderstorm         |

**Notes:**
- Returns numeric types (not strings).
- Very flexible: request only the variables you need.
- No API key required.
- Free tier is **non-commercial only**.

---

## Comparison for This Application

The City List app is a **no-server, vanilla JS frontend**. This imposes specific constraints:

| Criterion                        | wttr.in            | OpenWeatherMap     | Open-Meteo         |
|----------------------------------|--------------------|--------------------|---------------------|
| **No API key needed**            | Yes                | No (key in JS)     | Yes                 |
| **CORS from browser**           | Yes                | Yes                | Yes                 |
| **API key security risk**        | N/A                | Key exposed in HTML | N/A                |
| **Rate limit (free)**            | Fair-use           | 1,000/day          | 10,000/day          |
| **Forecast days (free)**         | 3 days             | 5 days             | 16 days             |
| **Current conditions**           | Yes                | Yes                | Yes                 |
| **Accepts lat/lon**              | Yes                | Yes                | Yes (required)      |
| **Accepts city name**            | Yes                | Yes                | No                  |
| **Response format**              | JSON (strings)     | JSON (numbers)     | JSON (numbers)      |
| **Built-in weather icons**       | No (text codes)    | Yes (icon URLs)    | No (WMO codes)      |
| **Commercial use (free)**        | Yes                | Yes                | No                  |
| **Setup complexity**             | Zero               | Registration + key | Zero                |

---

## Recommendation: wttr.in

**wttr.in** is the recommended API for this application.

### Rationale

1. **No API key required.** Since the app has no server, any API key would be embedded in client-side JavaScript and visible to anyone inspecting the page. wttr.in eliminates this security concern entirely.

2. **Zero setup.** No registration, no key activation wait, no account management. A `fetch()` call to `https://wttr.in/{city}?format=j1` returns weather data immediately.

3. **City name and lat/lon support.** The app's `cities.json` includes both city names and coordinates. wttr.in accepts either, providing flexibility in how the integration is built.

4. **Sufficient data for the app's scope.** Current conditions + 3-day forecast with hourly breakdowns covers the typical city weather dashboard use case.

5. **CORS-friendly.** Works directly from browser JavaScript without a proxy.

6. **Commercial use permitted.** No licensing restrictions on the free tier.

### Recommended Integration Pattern

```javascript
async function fetchWeather(city) {
  const url = `https://wttr.in/${encodeURIComponent(city.name)}?format=j1`;
  const resp = await fetch(url);
  if (!resp.ok) throw new Error(`Weather fetch failed: ${resp.status}`);
  return resp.json();
}
```

For more precise results using coordinates:
```javascript
async function fetchWeather(city) {
  const url = `https://wttr.in/${city.lat},${city.lon}?format=j1`;
  const resp = await fetch(url);
  if (!resp.ok) throw new Error(`Weather fetch failed: ${resp.status}`);
  return resp.json();
}
```

### Fields to Display

From the `j1` response, the most useful fields for a city weather card:

| Display element     | JSON path                                  |
|--------------------|--------------------------------------------|
| Temperature        | `current_condition[0].temp_C`              |
| Feels like         | `current_condition[0].FeelsLikeC`          |
| Description        | `current_condition[0].weatherDesc[0].value`|
| Humidity           | `current_condition[0].humidity`            |
| Wind speed         | `current_condition[0].windspeedKmph`       |
| Wind direction     | `current_condition[0].winddir16Point`      |
| UV index           | `current_condition[0].uvIndex`             |
| Forecast high/low  | `weather[n].maxtempC` / `weather[n].mintempC` |
| Forecast date      | `weather[n].date`                          |

### Caveats

- **Rate limits are undocumented.** wttr.in operates on a fair-use policy. For a small city-browsing app this is fine, but weather fetches should be triggered by user interaction (clicking a city), not automatically for all 50 cities on page load.
- **Values are strings.** All numeric fields come back as strings; parse with `parseInt()` or `parseFloat()` before display or comparison.
- **3-day forecast only.** If longer forecasts are needed in the future, Open-Meteo (16 days, no key) is the best fallback.
- **No official SLA.** wttr.in is a community project. For a production commercial app, consider Open-Meteo (paid tier) or OpenWeatherMap as fallback options.

### Fallback: Open-Meteo

If wttr.in proves unreliable or longer forecasts are needed, **Open-Meteo** is the recommended fallback. It also requires no API key and provides up to 16-day forecasts. The trade-off is that it only accepts lat/lon (not city names) and the free tier is non-commercial.

```javascript
async function fetchWeatherFallback(city) {
  const url = `https://api.open-meteo.com/v1/forecast?latitude=${city.lat}&longitude=${city.lon}&current_weather=true&daily=temperature_2m_max,temperature_2m_min,weathercode&timezone=auto`;
  const resp = await fetch(url);
  if (!resp.ok) throw new Error(`Weather fetch failed: ${resp.status}`);
  return resp.json();
}
```
