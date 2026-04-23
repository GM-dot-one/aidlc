# Research: City List and Weather Data Sources

**Work Package:** #49
**Date:** 2026-04-23
**Status:** Complete

---

## Objective

Identify and evaluate potential sources for:
1. A structured list of cities (name, country, coordinates, population, timezone).
2. Current and forecast weather data for those cities.

The evaluation covers data accuracy, availability, cost, and ease of integration.

---

## 1. City List Sources

### 1.1 GeoNames

| Attribute       | Detail |
|-----------------|--------|
| **URL**         | geonames.org |
| **Format**      | Downloadable TSV/CSV dumps; REST API |
| **Coverage**    | ~12 million place names worldwide |
| **License**     | Creative Commons Attribution 4.0 |
| **Cost**        | Free (API: 20k credits/day on free tier; premium plans from ~$4/month) |
| **Update cadence** | Daily dumps |

**Pros:**
- Comprehensive global coverage with lat/lon, timezone, population, country code, and admin divisions.
- Fully downloadable — no API dependency at runtime.
- Well-established dataset used widely in production systems.

**Cons:**
- Raw dumps require cleanup (duplicate entries, inconsistent transliterations).
- Free API has strict rate limits; premium is cheap but adds a billing dependency.

### 1.2 OpenStreetMap / Nominatim

| Attribute       | Detail |
|-----------------|--------|
| **URL**         | nominatim.openstreetmap.org |
| **Format**      | REST API (JSON); downloadable PBF/XML planet files |
| **Coverage**    | Global |
| **License**     | ODbL (Open Database License) |
| **Cost**        | Free (self-hosted or public instance with strict rate limits: 1 req/sec) |
| **Update cadence** | Continuous community edits |

**Pros:**
- Extremely detailed geographic data.
- Self-hostable for full control over rate limits and uptime.
- Active community keeps data fresh.

**Cons:**
- Extracting a clean city list from the full planet file requires non-trivial filtering (place=city/town/village tags).
- Public Nominatim instance is not suitable for production traffic.
- Data quality varies by region — excellent in Europe, sometimes sparse in parts of Africa/Asia.

### 1.3 SimpleMaps World Cities Database

| Attribute       | Detail |
|-----------------|--------|
| **URL**         | simplemaps.com/data/world-cities |
| **Format**      | CSV download |
| **Coverage**    | ~47k cities (free); ~4.4 million places (paid) |
| **License**     | Free (basic, CC BY 4.0); paid ($99 one-time for comprehensive) |
| **Cost**        | Free tier or $99 one-time |
| **Update cadence** | Periodic (roughly quarterly) |

**Pros:**
- Pre-cleaned, ready-to-use CSV with city, lat, lon, country, population, timezone.
- No API dependency — bundle directly in the application.
- One-time cost for the comprehensive dataset.

**Cons:**
- Free tier limited to ~47k entries (still sufficient for most weather apps targeting major cities).
- Less frequently updated than GeoNames.
- Commercial license required for redistribution of the paid tier.

---

## 2. Weather Data Sources

### 2.1 Open-Meteo

| Attribute       | Detail |
|-----------------|--------|
| **URL**         | open-meteo.com |
| **Format**      | REST API (JSON) |
| **Coverage**    | Global (1 km resolution in many regions) |
| **License**     | CC BY 4.0 for open data; API is free for non-commercial use |
| **Cost**        | Free (non-commercial, <10k requests/day); commercial plans from EUR 15/month |
| **Rate limits** | 10,000 requests/day (free); higher on paid plans |
| **Data scope**  | Current conditions, hourly/daily forecasts (16 days), historical data back to 1940 |

**Pros:**
- No API key required for the free tier — simplest possible integration.
- Combines multiple national weather services (DWD, NOAA, MeteoFrance, etc.) for global coverage.
- Historical weather data included at no extra cost.
- Self-hostable (open-source) if full control is needed.

**Cons:**
- Commercial use requires a paid subscription.
- Community-run; no SLA on the free tier.
- Newer service compared to established incumbents.

### 2.2 OpenWeatherMap

| Attribute       | Detail |
|-----------------|--------|
| **URL**         | openweathermap.org/api |
| **Format**      | REST API (JSON, XML) |
| **Coverage**    | Global (200,000+ cities) |
| **License**     | Proprietary |
| **Cost**        | Free (1,000 calls/day); paid plans from $0 (up to 1,000 calls/day) to ~$40/month (Professional, 60 calls/min) |
| **Rate limits** | Varies by plan; free tier: 60 calls/min, 1,000 calls/day |
| **Data scope**  | Current weather, 5-day/3-hour forecast (free); 16-day daily forecast, 30-day climate forecast, air pollution, geocoding (paid) |

**Pros:**
- Industry standard; massive community and extensive documentation.
- Built-in city geocoding API (can double as a city list source).
- Generous free tier for development and small-scale production.
- SDKs and community libraries available in most languages.

**Cons:**
- Free tier limited to 5-day forecast; 16-day requires a paid plan.
- Data accuracy can lag behind national weather services in some regions.
- Historical data requires a separate (paid) API.

### 2.3 WeatherAPI.com

| Attribute       | Detail |
|-----------------|--------|
| **URL**         | weatherapi.com |
| **Format**      | REST API (JSON, XML) |
| **Coverage**    | Global (2.8 million+ locations) |
| **License**     | Proprietary |
| **Cost**        | Free (1 million calls/month); paid from $9/month (2 million calls/month) |
| **Rate limits** | Free: ~23 calls/sec sustained |
| **Data scope**  | Current, forecast (14 days), historical, astronomy, time zone, sports, marine weather |

**Pros:**
- Very generous free tier (1 million calls/month).
- Single API covers weather, astronomy, timezone, and location search.
- 14-day forecast available on the free tier.
- Built-in autocomplete search for cities.

**Cons:**
- Smaller company; less community ecosystem than OpenWeatherMap.
- Free tier includes branding requirements.
- Historical data is limited to 7 days on free tier (paid required for deeper history).

### 2.4 National Weather Service APIs (NOAA, DWD, Met Office)

| Attribute       | Detail |
|-----------------|--------|
| **URL**         | weather.gov/documentation/services-web-api (NOAA); others vary by country |
| **Format**      | REST API (JSON/GeoJSON) |
| **Coverage**    | Country-specific (NOAA: US only; DWD: Germany/Europe; Met Office: UK) |
| **License**     | Public domain (NOAA) / Open Government License (Met Office) |
| **Cost**        | Free |
| **Data scope**  | Authoritative forecasts and observations for the covered region |

**Pros:**
- Highest accuracy for their respective regions — these are the source data other APIs aggregate.
- Completely free with no commercial restrictions.
- No API key required (NOAA).

**Cons:**
- Each covers only one country/region — a global app needs to aggregate multiple services.
- APIs differ in format, conventions, and reliability.
- No unified rate-limit guarantees; uptime is best-effort.

---

## 3. Comparison Matrix

| Criterion | Open-Meteo | OpenWeatherMap | WeatherAPI.com | National APIs |
|-----------|-----------|----------------|----------------|---------------|
| **Free tier generosity** | Good (10k/day) | Moderate (1k/day) | Excellent (1M/month) | Unlimited |
| **Forecast range (free)** | 16 days | 5 days | 14 days | Varies |
| **Historical data** | Yes (free) | Paid only | Paid (7+ days) | Yes (often) |
| **Global coverage** | Yes | Yes | Yes | No (per-country) |
| **API key required** | No | Yes | Yes | Varies |
| **Commercial use (free tier)** | No | Yes | With branding | Yes |
| **Built-in city search** | No | Yes | Yes | No |
| **Self-hostable** | Yes | No | No | N/A |
| **Community/maturity** | Growing | Large | Medium | Authoritative |

---

## 4. Recommendations

### City List: GeoNames

**GeoNames** is the recommended city list source. It provides the most comprehensive, freely downloadable, regularly updated dataset with all the fields needed (name, coordinates, country, population, timezone). The `cities15000.txt` dump (~25k cities with population > 15,000) is a practical starting point that covers all significant cities worldwide while remaining small enough to bundle or load into a database.

**Fallback:** If a smaller, pre-cleaned dataset is preferred and the scope is limited to major cities, the SimpleMaps free tier (~47k cities, ready-to-use CSV) is an excellent zero-effort alternative.

### Weather Data: Open-Meteo (primary) + OpenWeatherMap (fallback)

**Open-Meteo** is recommended as the primary weather data source for the following reasons:
- No API key required — simplest integration path.
- 16-day forecast on the free tier (vs. 5-day for OpenWeatherMap).
- Historical data included at no extra cost.
- Aggregates authoritative national weather services for high accuracy.
- Self-hostable if the project needs to eliminate third-party runtime dependencies.

**OpenWeatherMap** is recommended as a secondary/fallback source:
- It provides a built-in city geocoding API, which is useful as a cross-reference for the GeoNames city list.
- It has the largest community and the most battle-tested infrastructure.
- Its free tier allows commercial use without restrictions.

### Integration Strategy

1. **City list:** Download GeoNames `cities15000.txt` at build/deploy time. Parse into a local SQLite or PostgreSQL table. Refresh periodically (weekly or monthly) via a scheduled job.
2. **Weather data:** Call Open-Meteo's forecast API at request time, passing lat/lon from the city table. Cache responses (weather data is inherently short-lived; a 15–30 minute TTL is reasonable).
3. **Fallback:** If Open-Meteo is unavailable, fall back to OpenWeatherMap. Both APIs accept lat/lon, so the calling code stays the same.

---

## 5. Follow-Up Considerations

- **Rate limiting and caching:** Even with generous free tiers, a caching layer (Redis or in-memory) is essential to avoid hitting limits when serving many users.
- **Terms of service:** Open-Meteo's free tier is non-commercial. If the project is commercial, budget EUR 15/month for Open-Meteo or use OpenWeatherMap's free tier (which permits commercial use).
- **Data freshness:** Weather data should be fetched on demand (not pre-fetched for all cities), since forecasts change frequently and most cities will never be queried.
- **Licensing for city data:** GeoNames CC-BY-4.0 requires attribution. Ensure the application includes proper attribution.
