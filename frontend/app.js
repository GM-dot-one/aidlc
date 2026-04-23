"use strict";

const cityList = document.getElementById("city-list");
const searchInput = document.getElementById("search");
const sortSelect = document.getElementById("sort");
const cityCount = document.getElementById("city-count");

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

function renderCities(list) {
  cityCount.textContent = list.length + " " + (list.length === 1 ? "city" : "cities");

  if (list.length === 0) {
    cityList.innerHTML = '<div class="empty-state">No cities match your search.</div>';
    return;
  }

  cityList.innerHTML = list
    .map(
      (c) => `
    <article class="city-card">
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
