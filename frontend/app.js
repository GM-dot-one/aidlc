"use strict";

var cityListEl = document.getElementById("city-list");
var searchInput = document.getElementById("search");
var cityCountEl = document.getElementById("city-count");
var weatherPanel = document.getElementById("weather-panel");
var emptyState = document.getElementById("empty-state");
var btnC = document.getElementById("btn-c");
var btnF = document.getElementById("btn-f");

var cities = [];
var selectedCity = null;
var weatherCache = {};
var useFahrenheit = false;

var WMO_CODES = {
  0:  { description: "Clear sky",            icon: "☀️" },
  1:  { description: "Mainly clear",         icon: "🌤️" },
  2:  { description: "Partly cloudy",        icon: "⛅" },
  3:  { description: "Overcast",             icon: "☁️" },
  45: { description: "Fog",                  icon: "🌫️" },
  48: { description: "Freezing fog",         icon: "🌫️" },
  51: { description: "Light drizzle",        icon: "🌦️" },
  53: { description: "Moderate drizzle",     icon: "🌦️" },
  55: { description: "Dense drizzle",        icon: "🌧️" },
  56: { description: "Freezing drizzle",     icon: "🌨️" },
  57: { description: "Dense freezing drizzle", icon: "🌨️" },
  61: { description: "Slight rain",          icon: "🌧️" },
  63: { description: "Moderate rain",        icon: "🌧️" },
  65: { description: "Heavy rain",           icon: "🌧️" },
  66: { description: "Freezing rain",        icon: "🌨️" },
  67: { description: "Heavy freezing rain",  icon: "🌨️" },
  71: { description: "Slight snowfall",      icon: "🌨️" },
  73: { description: "Moderate snowfall",    icon: "🌨️" },
  75: { description: "Heavy snowfall",       icon: "🌨️" },
  77: { description: "Snow grains",          icon: "🌨️" },
  80: { description: "Slight rain showers",  icon: "🌦️" },
  81: { description: "Moderate rain showers",icon: "🌧️" },
  82: { description: "Violent rain showers", icon: "🌧️" },
  85: { description: "Slight snow showers",  icon: "🌨️" },
  86: { description: "Heavy snow showers",   icon: "🌨️" },
  95: { description: "Thunderstorm",         icon: "⛈️" },
  96: { description: "Thunderstorm with hail", icon: "⛈️" },
  99: { description: "Thunderstorm with heavy hail", icon: "⛈️" }
};

var DAY_NAMES = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

function cToF(c) {
  return Math.round(c * 9 / 5 + 32);
}

function tempStr(c) {
  if (useFahrenheit) return cToF(c) + "°F";
  return Math.round(c) + "°C";
}

function getWeatherInfo(code) {
  return WMO_CODES[code] || { description: "Unknown", icon: "❓" };
}

function timeAgo(isoString) {
  var diff = Math.floor((Date.now() - new Date(isoString).getTime()) / 60000);
  if (diff < 1) return "just now";
  if (diff === 1) return "1 minute ago";
  if (diff < 60) return diff + " minutes ago";
  var hours = Math.floor(diff / 60);
  if (hours === 1) return "1 hour ago";
  return hours + " hours ago";
}

function getCacheKey(city) {
  return city.lat + "," + city.lon;
}

function isCacheFresh(entry) {
  return entry && (Date.now() - entry.fetchedAt < 5 * 60 * 1000);
}

async function fetchWeather(city) {
  var key = getCacheKey(city);
  if (isCacheFresh(weatherCache[key])) {
    return weatherCache[key].data;
  }

  var params = new URLSearchParams({
    latitude: city.lat,
    longitude: city.lon,
    current: "temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code,apparent_temperature,surface_pressure",
    daily: "weather_code,temperature_2m_max,temperature_2m_min",
    forecast_days: "5",
    timezone: "auto"
  });

  var resp = await fetch("https://api.open-meteo.com/v1/forecast?" + params.toString());
  if (!resp.ok) throw new Error("Weather API error: " + resp.status);

  var data = await resp.json();
  if (!data.current) throw new Error("No current weather data available");

  weatherCache[key] = { data: data, fetchedAt: Date.now() };
  return data;
}

function renderCityList() {
  var query = searchInput.value.toLowerCase().trim();
  var filtered = cities;
  if (query) {
    filtered = cities.filter(function (c) {
      return c.name.toLowerCase().includes(query) || c.country.toLowerCase().includes(query);
    });
  }

  filtered.sort(function (a, b) { return a.name.localeCompare(b.name); });
  cityCountEl.textContent = filtered.length + " " + (filtered.length === 1 ? "city" : "cities");

  if (filtered.length === 0) {
    cityListEl.innerHTML = '<li class="city-list-loading">No cities match your search.</li>';
    return;
  }

  cityListEl.innerHTML = filtered.map(function (c) {
    var isSelected = selectedCity && c.name === selectedCity.name;
    var cacheKey = getCacheKey(c);
    var cached = weatherCache[cacheKey];
    var weatherHtml = "";

    if (cached && cached.data && cached.data.current) {
      var cur = cached.data.current;
      var info = getWeatherInfo(cur.weather_code);
      weatherHtml =
        '<div class="city-card-weather">' +
          '<div class="temp">' + tempStr(cur.temperature_2m) + '</div>' +
          '<div class="condition">' + info.icon + ' ' + info.description + '</div>' +
        '</div>';
    }

    return '<li class="city-card' + (isSelected ? " selected" : "") + '"' +
      ' role="option" aria-selected="' + (isSelected ? "true" : "false") + '"' +
      ' data-city="' + c.name + '">' +
      '<div class="city-card-info"><h3>' + c.name + '</h3>' +
      '<span>' + c.country + '</span></div>' +
      weatherHtml + '</li>';
  }).join("");
}

function renderWeatherLoading() {
  emptyState.style.display = "none";
  weatherPanel.innerHTML =
    '<div class="loading-state">' +
      '<div class="loading-spinner"></div>' +
      '<p>Loading weather data...</p>' +
    '</div>';
}

function renderWeatherError(city, error) {
  emptyState.style.display = "none";
  weatherPanel.innerHTML =
    '<div class="weather-header"><h1>' + city.name + ', ' + city.country + '</h1></div>' +
    '<div class="error-banner">' +
      '<span>Could not load weather data. ' + (error.message || "Please try again.") + '</span>' +
      '<button id="retry-btn">Retry</button>' +
    '</div>';

  document.getElementById("retry-btn").addEventListener("click", function () {
    var key = getCacheKey(city);
    delete weatherCache[key];
    selectCity(city);
  });
}

function renderWeather(city, data) {
  emptyState.style.display = "none";

  var cur = data.current;
  var info = getWeatherInfo(cur.weather_code);

  var forecastHtml = "";
  if (data.daily && data.daily.time) {
    forecastHtml = data.daily.time.map(function (dateStr, i) {
      var d = new Date(dateStr + "T00:00:00");
      var dayInfo = getWeatherInfo(data.daily.weather_code[i]);
      return '<div class="forecast-day">' +
        '<div class="day-label">' + DAY_NAMES[d.getDay()] + '</div>' +
        '<div class="day-icon">' + dayInfo.icon + '</div>' +
        '<div class="day-temp">' + tempStr(data.daily.temperature_2m_max[i]) + '</div>' +
        '<div class="day-temp-low">' + tempStr(data.daily.temperature_2m_min[i]) + '</div>' +
      '</div>';
    }).join("");
  }

  var updatedText = cur.time ? "Last updated: " + timeAgo(cur.time) : "";

  weatherPanel.innerHTML =
    '<div class="weather-header">' +
      '<h1>' + city.name + ', ' + city.country + '</h1>' +
      '<div class="updated">' + updatedText + '</div>' +
    '</div>' +
    '<div class="current-weather">' +
      '<div class="weather-icon" aria-label="' + info.description + '">' + info.icon + '</div>' +
      '<div class="temp-block">' +
        '<div class="temp-value">' + tempStr(cur.temperature_2m) + '</div>' +
        '<div class="condition-label">' + info.description + '</div>' +
        '<div class="feels-like">Feels like ' + tempStr(cur.apparent_temperature) + '</div>' +
      '</div>' +
    '</div>' +
    '<div class="detail-row">' +
      '<div class="detail-card">' +
        '<div class="detail-icon">💧</div>' +
        '<div class="detail-value">' + Math.round(cur.relative_humidity_2m) + '%</div>' +
        '<div class="detail-label">Humidity</div>' +
      '</div>' +
      '<div class="detail-card">' +
        '<div class="detail-icon">🌬️</div>' +
        '<div class="detail-value">' + Math.round(cur.wind_speed_10m) + ' km/h</div>' +
        '<div class="detail-label">Wind</div>' +
      '</div>' +
      '<div class="detail-card">' +
        '<div class="detail-icon">📈</div>' +
        '<div class="detail-value">' + Math.round(cur.surface_pressure) + ' hPa</div>' +
        '<div class="detail-label">Pressure</div>' +
      '</div>' +
    '</div>' +
    (forecastHtml ?
      '<div class="forecast-section"><h2>5-Day Forecast</h2>' +
        '<div class="forecast-row">' + forecastHtml + '</div>' +
      '</div>' : "");
}

async function selectCity(city) {
  selectedCity = city;
  renderCityList();
  renderWeatherLoading();

  try {
    var data = await fetchWeather(city);
    if (selectedCity && selectedCity.name === city.name) {
      renderWeather(city, data);
      renderCityList();
    }
  } catch (err) {
    if (selectedCity && selectedCity.name === city.name) {
      renderWeatherError(city, err);
    }
    console.error("Weather fetch failed:", err);
  }
}

function handleCityClick(e) {
  var card = e.target.closest(".city-card");
  if (!card) return;
  var name = card.getAttribute("data-city");
  var city = cities.find(function (c) { return c.name === name; });
  if (city) selectCity(city);
}

function handleUnitToggle(toFahrenheit) {
  useFahrenheit = toFahrenheit;
  btnC.classList.toggle("active", !toFahrenheit);
  btnC.setAttribute("aria-checked", !toFahrenheit ? "true" : "false");
  btnF.classList.toggle("active", toFahrenheit);
  btnF.setAttribute("aria-checked", toFahrenheit ? "true" : "false");
  renderCityList();
  if (selectedCity) {
    var key = getCacheKey(selectedCity);
    var cached = weatherCache[key];
    if (cached && cached.data) {
      renderWeather(selectedCity, cached.data);
    }
  }
}

async function init() {
  cityListEl.innerHTML = '<li class="city-list-loading">Loading cities…</li>';

  try {
    var resp = await fetch("cities.json");
    if (!resp.ok) throw new Error("Failed to load cities.json: " + resp.status);
    cities = await resp.json();
    renderCityList();
  } catch (err) {
    cityListEl.innerHTML =
      '<li class="city-list-error">Could not load city data. Serve this directory with an HTTP server (e.g. <code>make serve-frontend</code>).</li>';
    console.error(err);
  }
}

searchInput.addEventListener("input", renderCityList);
cityListEl.addEventListener("click", handleCityClick);
btnC.addEventListener("click", function () { handleUnitToggle(false); });
btnF.addEventListener("click", function () { handleUnitToggle(true); });

init();
