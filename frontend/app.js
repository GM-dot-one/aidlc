"use strict";

const cityList = document.getElementById("city-list");
const searchInput = document.getElementById("search");
const sortSelect = document.getElementById("sort");
const cityCount = document.getElementById("city-count");
const weatherPanel = document.getElementById("weather-panel");

const OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast";
const CURRENT_PARAMS = "temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code";

const WMO_DESCRIPTIONS = {
  0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
  45: "Fog", 48: "Depositing rime fog",
  51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
  61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
  71: "Slight snowfall", 73: "Moderate snowfall", 75: "Heavy snowfall",
  80: "Slight rain showers", 81: "Moderate rain showers", 82: "Violent rain showers",
  95: "Thunderstorm", 96: "Thunderstorm with slight hail", 99: "Thunderstorm with heavy hail",
};

let cities = [];

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

async function fetchWeather(city) {
  const url = new URL(OPEN_METEO_URL);
  url.searchParams.set("latitude", city.lat);
  url.searchParams.set("longitude", city.lon);
  url.searchParams.set("current", CURRENT_PARAMS);

  const resp = await fetch(url);
  if (!resp.ok) throw new Error("Weather API error: " + resp.status);
  const data = await resp.json();

  console.log("Weather API response for " + city.name + ":", data);

  const current = data.current;
  if (!current) throw new Error("No current weather data in response");

  return {
    temperature: current.temperature_2m,
    humidity: current.relative_humidity_2m,
    windSpeed: current.wind_speed_10m,
    weatherCode: current.weather_code,
    description: WMO_DESCRIPTIONS[current.weather_code] || "Unknown (" + current.weather_code + ")",
  };
}

function showWeatherPanel(city, weather) {
  weatherPanel.innerHTML = `
    <div class="weather-header">
      <span class="weather-city">${city.name}, ${city.country}</span>
      <button id="close-weather" class="close-btn" aria-label="Close">&times;</button>
    </div>
    <div class="weather-details">
      <div class="weather-temp">${weather.temperature}°C</div>
      <div class="weather-desc">${weather.description}</div>
      <div class="weather-stats">
        <span>Humidity: ${weather.humidity}%</span>
        <span>Wind: ${weather.windSpeed} km/h</span>
      </div>
    </div>`;
  weatherPanel.hidden = false;
  document.getElementById("close-weather").addEventListener("click", () => {
    weatherPanel.hidden = true;
  });
}

function showWeatherError(city, err) {
  weatherPanel.innerHTML = `
    <div class="weather-header">
      <span class="weather-city">${city.name}</span>
      <button id="close-weather" class="close-btn" aria-label="Close">&times;</button>
    </div>
    <div class="weather-error">Could not load weather data. ${err.message}</div>`;
  weatherPanel.hidden = false;
  document.getElementById("close-weather").addEventListener("click", () => {
    weatherPanel.hidden = true;
  });
}

async function handleCityClick(city) {
  weatherPanel.innerHTML = '<div class="weather-loading">Loading weather…</div>';
  weatherPanel.hidden = false;
  try {
    const weather = await fetchWeather(city);
    showWeatherPanel(city, weather);
  } catch (err) {
    console.error("Failed to fetch weather for " + city.name + ":", err);
    showWeatherError(city, err);
  }
}

function renderCities(list) {
  cityCount.textContent = list.length + " " + (list.length === 1 ? "city" : "cities");

  if (list.length === 0) {
    cityList.innerHTML = '<div class="empty-state">No cities match your search.</div>';
    return;
  }

  cityList.innerHTML = list
    .map(
      (c, i) => `
    <article class="city-card" data-index="${i}" role="button" tabindex="0">
      <div class="city-info">
        <span class="city-name">${c.name}</span>
        <span class="city-country">${c.country}</span>
      </div>
      <div class="city-meta">
        <span class="city-population">Pop. ${formatPopulation(c.population)}</span>
        <span class="city-coords">${formatCoord(c.lat, c.lon)}</span>
      </div>
    </article>`
    )
    .join("");

  cityList.querySelectorAll(".city-card").forEach((card) => {
    const city = list[Number(card.dataset.index)];
    card.addEventListener("click", () => handleCityClick(city));
    card.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        handleCityClick(city);
      }
    });
  });
}

function getFilteredAndSorted() {
  const query = searchInput.value.toLowerCase().trim();
  const sortBy = sortSelect.value;

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
  cityList.innerHTML = '<div class="loading-state">Loading cities…</div>';

  try {
    const resp = await fetch("cities.json");
    if (!resp.ok) throw new Error("Failed to load cities.json: " + resp.status);
    cities = await resp.json();
    update();
  } catch (err) {
    cityList.innerHTML =
      '<div class="error-state">Could not load city data. Serve this directory with an HTTP server (e.g. <code>make serve-frontend</code>).</div>';
    console.error(err);
  }
}

searchInput.addEventListener("input", update);
sortSelect.addEventListener("change", update);

init();
