"use strict";

let cities = [];
let savedContainerHTML = "";

function formatPopulation(n) {
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + "M";
  if (n >= 1_000) return (n / 1_000).toFixed(0) + "K";
  return n.toString();
}

function formatCoord(lat, lon) {
  const latDir = lat >= 0 ? "N" : "S";
  const lonDir = lon >= 0 ? "E" : "W";
  return Math.abs(lat).toFixed(2) + "°" + latDir + ", " + Math.abs(lon).toFixed(2) + "°" + lonDir;
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

const WEATHER_CODE_MAP = {
  113: { label: "Sunny", icon: "☀️", gradient: "linear-gradient(135deg, #f59e0b, #fbbf24)" },
  116: { label: "Partly Cloudy", icon: "⛅", gradient: "linear-gradient(135deg, #60a5fa, #93c5fd)" },
  119: { label: "Cloudy", icon: "☁️", gradient: "linear-gradient(135deg, #9ca3af, #d1d5db)" },
  122: { label: "Overcast", icon: "☁️", gradient: "linear-gradient(135deg, #9ca3af, #d1d5db)" },
  143: { label: "Foggy", icon: "🌫️", gradient: "linear-gradient(135deg, #d1d5db, #e5e7eb)" },
  176: { label: "Rainy", icon: "🌧️", gradient: "linear-gradient(135deg, #3b82f6, #60a5fa)" },
  200: { label: "Stormy", icon: "⛈️", gradient: "linear-gradient(135deg, #7c3aed, #a78bfa)" },
  227: { label: "Snowy", icon: "❄️", gradient: "linear-gradient(135deg, #e0f2fe, #f0f9ff)" },
  230: { label: "Blizzard", icon: "❄️", gradient: "linear-gradient(135deg, #e0f2fe, #f0f9ff)" },
  248: { label: "Foggy", icon: "🌫️", gradient: "linear-gradient(135deg, #d1d5db, #e5e7eb)" },
  260: { label: "Foggy", icon: "🌫️", gradient: "linear-gradient(135deg, #d1d5db, #e5e7eb)" },
  263: { label: "Light Rain", icon: "🌧️", gradient: "linear-gradient(135deg, #3b82f6, #60a5fa)" },
  266: { label: "Light Rain", icon: "🌧️", gradient: "linear-gradient(135deg, #3b82f6, #60a5fa)" },
  281: { label: "Freezing Rain", icon: "🌧️", gradient: "linear-gradient(135deg, #3b82f6, #60a5fa)" },
  293: { label: "Rainy", icon: "🌧️", gradient: "linear-gradient(135deg, #3b82f6, #60a5fa)" },
  296: { label: "Rainy", icon: "🌧️", gradient: "linear-gradient(135deg, #3b82f6, #60a5fa)" },
  299: { label: "Heavy Rain", icon: "🌧️", gradient: "linear-gradient(135deg, #3b82f6, #60a5fa)" },
  302: { label: "Heavy Rain", icon: "🌧️", gradient: "linear-gradient(135deg, #3b82f6, #60a5fa)" },
  311: { label: "Freezing Rain", icon: "🌧️", gradient: "linear-gradient(135deg, #3b82f6, #60a5fa)" },
  320: { label: "Snowy", icon: "❄️", gradient: "linear-gradient(135deg, #e0f2fe, #f0f9ff)" },
  323: { label: "Snowy", icon: "❄️", gradient: "linear-gradient(135deg, #e0f2fe, #f0f9ff)" },
  326: { label: "Snowy", icon: "❄️", gradient: "linear-gradient(135deg, #e0f2fe, #f0f9ff)" },
  329: { label: "Heavy Snow", icon: "❄️", gradient: "linear-gradient(135deg, #e0f2fe, #f0f9ff)" },
  332: { label: "Heavy Snow", icon: "❄️", gradient: "linear-gradient(135deg, #e0f2fe, #f0f9ff)" },
  338: { label: "Heavy Snow", icon: "❄️", gradient: "linear-gradient(135deg, #e0f2fe, #f0f9ff)" },
  350: { label: "Hail", icon: "🌨️", gradient: "linear-gradient(135deg, #7c3aed, #a78bfa)" },
  353: { label: "Light Rain", icon: "🌧️", gradient: "linear-gradient(135deg, #3b82f6, #60a5fa)" },
  356: { label: "Heavy Rain", icon: "🌧️", gradient: "linear-gradient(135deg, #3b82f6, #60a5fa)" },
  359: { label: "Torrential Rain", icon: "🌧️", gradient: "linear-gradient(135deg, #3b82f6, #60a5fa)" },
  362: { label: "Sleet", icon: "🌨️", gradient: "linear-gradient(135deg, #e0f2fe, #f0f9ff)" },
  365: { label: "Heavy Sleet", icon: "🌨️", gradient: "linear-gradient(135deg, #e0f2fe, #f0f9ff)" },
  368: { label: "Light Snow", icon: "❄️", gradient: "linear-gradient(135deg, #e0f2fe, #f0f9ff)" },
  371: { label: "Heavy Snow", icon: "❄️", gradient: "linear-gradient(135deg, #e0f2fe, #f0f9ff)" },
  374: { label: "Hail", icon: "🌨️", gradient: "linear-gradient(135deg, #7c3aed, #a78bfa)" },
  377: { label: "Heavy Hail", icon: "🌨️", gradient: "linear-gradient(135deg, #7c3aed, #a78bfa)" },
  386: { label: "Stormy", icon: "⛈️", gradient: "linear-gradient(135deg, #7c3aed, #a78bfa)" },
  389: { label: "Stormy", icon: "⛈️", gradient: "linear-gradient(135deg, #7c3aed, #a78bfa)" },
  392: { label: "Snow Storm", icon: "⛈️", gradient: "linear-gradient(135deg, #7c3aed, #a78bfa)" },
  395: { label: "Heavy Snow Storm", icon: "⛈️", gradient: "linear-gradient(135deg, #7c3aed, #a78bfa)" },
};

const DEFAULT_CONDITION = { label: "Unknown", icon: "❓", gradient: "linear-gradient(135deg, #9ca3af, #d1d5db)" };

function getCondition(weatherCode) {
  return WEATHER_CODE_MAP[weatherCode] || DEFAULT_CONDITION;
}

function renderCities(list) {
  const cityListEl = document.getElementById("city-list");
  const cityCountEl = document.getElementById("city-count");
  if (!cityListEl || !cityCountEl) return;

  cityCountEl.textContent = list.length + " " + (list.length === 1 ? "city" : "cities");

  if (list.length === 0) {
    cityListEl.innerHTML = '<div class="empty-state">No cities match your search.</div>';
    return;
  }

  cityListEl.innerHTML = list
    .map(
      (c) => `
    <article class="city-card" data-city-name="${escapeHtml(c.name)}" data-city-country="${escapeHtml(c.country)}" data-lat="${c.lat}" data-lon="${c.lon}" role="button" tabindex="0" aria-label="View weather for ${escapeHtml(c.name)}, ${escapeHtml(c.country)}">
      <div class="city-info">
        <span class="city-name">${escapeHtml(c.name)}</span>
        <span class="city-country">${escapeHtml(c.country)}</span>
      </div>
      <div class="city-meta">
        <span class="city-population">Pop. ${formatPopulation(c.population)}</span>
        <span class="city-coords">${formatCoord(c.lat, c.lon)}</span>
      </div>
    </article>`
    )
    .join("");

  cityListEl.querySelectorAll(".city-card").forEach((card) => {
    card.addEventListener("click", () => showWeather(card.dataset));
    card.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        showWeather(card.dataset);
      }
    });
  });
}

function renderWeatherLoading(cityName, country) {
  const container = document.querySelector(".container");
  container.innerHTML = `
    <div class="weather-display">
      <button class="back-btn" aria-label="Back to city list">&larr; Back to city list</button>
      <div class="weather-header-section">
        <h1 class="weather-city-name">${escapeHtml(cityName)}, ${escapeHtml(country)}</h1>
        <p class="weather-updated">Loading weather data&hellip;</p>
      </div>
      <div class="weather-hero weather-hero--loading">
        <div class="weather-hero-icon" aria-hidden="true"></div>
        <div class="weather-hero-data">
          <div class="skeleton-block" style="height:2.5rem;width:200px"></div>
          <div class="skeleton-block" style="height:1.25rem;width:140px;margin-top:0.5rem"></div>
        </div>
      </div>
      <div class="weather-details">
        <div class="detail-card"><div class="skeleton-block" style="height:60px"></div></div>
        <div class="detail-card"><div class="skeleton-block" style="height:60px"></div></div>
        <div class="detail-card"><div class="skeleton-block" style="height:60px"></div></div>
      </div>
    </div>`;

  container.querySelector(".back-btn").addEventListener("click", restoreCityList);
}

function renderWeatherDisplay(data, cityName, country, lat, lon) {
  const cond = data.current_condition[0];
  const weatherCode = parseInt(cond.weatherCode, 10);
  const condition = getCondition(weatherCode);
  const tempC = escapeHtml(cond.temp_C);
  const tempF = escapeHtml(cond.temp_F);
  const humidity = escapeHtml(cond.humidity);
  const windKmph = escapeHtml(cond.windspeedKmph);
  const description = escapeHtml(cond.weatherDesc[0].value);
  const observationTime = escapeHtml(cond.observation_time);

  const container = document.querySelector(".container");
  container.innerHTML = `
    <div class="weather-display">
      <button class="back-btn" aria-label="Back to city list">&larr; Back to city list</button>

      <div class="weather-header-section">
        <h1 class="weather-city-name">${escapeHtml(cityName)}, ${escapeHtml(country)}</h1>
        <p class="weather-updated">Last updated: ${observationTime} UTC</p>
      </div>

      <div class="weather-hero" style="background: ${condition.gradient}">
        <div class="weather-hero-icon" aria-label="${description}">${condition.icon}</div>
        <div class="weather-hero-data">
          <div class="weather-temp">${tempC}&deg;C <span class="weather-temp-alt">/ ${tempF}&deg;F</span></div>
          <div class="weather-condition">${description}</div>
        </div>
      </div>

      <div class="weather-details">
        <div class="detail-card">
          <div class="detail-card-icon" aria-hidden="true">💧</div>
          <div class="detail-card-value">${humidity}%</div>
          <div class="detail-card-label">Humidity</div>
        </div>
        <div class="detail-card">
          <div class="detail-card-icon" aria-hidden="true">🌬️</div>
          <div class="detail-card-value">${windKmph} km/h</div>
          <div class="detail-card-label">Wind</div>
        </div>
        <div class="detail-card">
          <div class="detail-card-icon" aria-hidden="true">📍</div>
          <div class="detail-card-value">${formatCoord(parseFloat(lat), parseFloat(lon))}</div>
          <div class="detail-card-label">Coordinates</div>
        </div>
      </div>

      <p class="weather-timestamp">Observation: ${observationTime} UTC</p>
    </div>`;

  container.querySelector(".back-btn").addEventListener("click", restoreCityList);
}

function renderWeatherError(cityName, country, dataset) {
  const container = document.querySelector(".container");
  container.innerHTML = `
    <div class="weather-display">
      <button class="back-btn" aria-label="Back to city list">&larr; Back to city list</button>
      <div class="weather-header-section">
        <h1 class="weather-city-name">${escapeHtml(cityName)}, ${escapeHtml(country)}</h1>
      </div>
      <div class="weather-error">
        <p>Could not load weather data. Please try again.</p>
        <button class="retry-btn">Retry</button>
      </div>
    </div>`;

  container.querySelector(".back-btn").addEventListener("click", restoreCityList);
  container.querySelector(".retry-btn").addEventListener("click", () => showWeather(dataset));
}

async function showWeather(dataset) {
  const { cityName, cityCountry, lat, lon } = dataset;
  renderWeatherLoading(cityName, cityCountry);

  try {
    const url = "https://wttr.in/" + encodeURIComponent(cityName) + "?format=j1";
    const resp = await fetch(url);
    if (!resp.ok) throw new Error("HTTP " + resp.status);
    const data = await resp.json();
    renderWeatherDisplay(data, cityName, cityCountry, lat, lon);
  } catch (err) {
    console.error("Weather fetch failed:", err);
    renderWeatherError(cityName, cityCountry, dataset);
  }
}

function restoreCityList() {
  const container = document.querySelector(".container");
  container.innerHTML = savedContainerHTML;
  renderCities(getFilteredAndSorted());

  document.getElementById("search").addEventListener("input", update);
  document.getElementById("sort").addEventListener("change", update);
}

function getFilteredAndSorted() {
  const searchEl = document.getElementById("search");
  const sortEl = document.getElementById("sort");
  const query = searchEl ? searchEl.value.toLowerCase().trim() : "";
  const sortBy = sortEl ? sortEl.value : "name";

  let filtered = cities;
  if (query) {
    filtered = cities.filter(
      (c) => c.name.toLowerCase().includes(query) || c.country.toLowerCase().includes(query)
    );
  }

  const sorted = [...filtered];
  switch (sortBy) {
    case "name":
      sorted.sort((a, b) => a.name.localeCompare(b.name));
      break;
    case "country":
      sorted.sort((a, b) => a.country.localeCompare(b.country) || a.name.localeCompare(b.name));
      break;
    case "population":
      sorted.sort((a, b) => b.population - a.population);
      break;
  }

  return sorted;
}

function update() {
  renderCities(getFilteredAndSorted());
}

async function init() {
  const cl = document.getElementById("city-list");
  cl.innerHTML = '<div class="loading-state">Loading cities…</div>';

  try {
    const resp = await fetch("cities.json");
    if (!resp.ok) throw new Error("Failed to load cities.json: " + resp.status);
    cities = await resp.json();
    update();
    savedContainerHTML = document.querySelector(".container").innerHTML;
  } catch (err) {
    cl.innerHTML =
      '<div class="error-state">Could not load city data. Serve this directory with an HTTP server (e.g. <code>make serve-frontend</code>).</div>';
    console.error(err);
  }
}

document.getElementById("search").addEventListener("input", update);
document.getElementById("sort").addEventListener("change", update);

init();
