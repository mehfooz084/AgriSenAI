import { getWeather } from "./api.js";

const form = document.getElementById("weather-form");
const cityInput = document.getElementById("city-input");
const loadingEl = document.getElementById("weather-loading");
const errorBox = document.getElementById("error-box");
const resultEl = document.getElementById("weather-result");
const locationEl = document.getElementById("location-card");
const tempEl = document.getElementById("metric-temp");
const humEl = document.getElementById("metric-hum");
const windEl = document.getElementById("metric-wind");
const recEl = document.getElementById("recommendation");
const forecastBody = document.getElementById("forecast-body");

let tempChart = null;
let rainChart = null;

function showError(message) {
  errorBox.textContent = message;
  errorBox.classList.remove("hidden");
}

function clearError() {
  errorBox.classList.add("hidden");
  errorBox.textContent = "";
}

function recClasses(status) {
  if (status === "success") {
    return "border-emerald-200 bg-emerald-50 text-emerald-900";
  }
  if (status === "warning") {
    return "border-amber-200 bg-amber-50 text-amber-950";
  }
  return "border-rose-200 bg-rose-50 text-rose-950";
}

function destroyCharts() {
  if (tempChart) {
    tempChart.destroy();
    tempChart = null;
  }
  if (rainChart) {
    rainChart.destroy();
    rainChart = null;
  }
}

function renderCharts(forecast) {
  const labels = forecast.map((row) => row["Date"]);
  const maxTemp = forecast.map((row) => Number(row["Max Temp (°C)"]));
  const minTemp = forecast.map((row) => Number(row["Min Temp (°C)"]));
  const rain = forecast.map((row) => Number(row["Rain Probability (%)"]));

  destroyCharts();

  const tempCanvas = document.getElementById("temp-chart");
  const rainCanvas = document.getElementById("rain-chart");

  const ChartLib = window.Chart;
  if (!ChartLib) {
    throw new Error("Chart library failed to load. Please refresh the page.");
  }

  tempChart = new ChartLib(tempCanvas, {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label: "Max Temperature",
          data: maxTemp,
          borderColor: "#166534",
          backgroundColor: "rgba(22, 101, 52, 0.08)",
          tension: 0.25,
          fill: true,
        },
        {
          label: "Min Temperature",
          data: minTemp,
          borderColor: "#65a30d",
          backgroundColor: "rgba(101, 163, 13, 0.08)",
          tension: 0.25,
          fill: true,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { position: "bottom" } },
      scales: { y: { title: { display: true, text: "°C" } } },
    },
  });

  rainChart = new ChartLib(rainCanvas, {
    type: "bar",
    data: {
      labels,
      datasets: [
        {
          label: "Rain Probability",
          data: rain,
          backgroundColor: "#0ea5e9",
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: { y: { beginAtZero: true, max: 100, title: { display: true, text: "%" } } },
    },
  });
}

function renderWeather(data) {
  const loc = data.location || {};
  const cur = data.current || {};
  const rec = data.recommendation || {};
  const forecast = Array.isArray(data.forecast) ? data.forecast : [];

  locationEl.innerHTML = `
    <p class="text-sm text-stone-500">Location</p>
    <h3 class="mt-1 text-xl font-semibold text-emerald-950">${loc.city || "-"}, ${loc.state || "-"}</h3>
    <p class="mt-2 text-sm text-stone-600">${loc.country || "-"}</p>
    <p class="mt-3 text-sm text-stone-500">Lat ${Number(loc.lat).toFixed(4)} · Lon ${Number(loc.lon).toFixed(4)}</p>
  `;

  tempEl.textContent = `${Number(cur.temp).toFixed(1)} °C`;
  humEl.textContent = `${Number(cur.hum).toFixed(0)} %`;
  windEl.textContent = `${Number(cur.wind).toFixed(1)} km/h`;

  recEl.className = `rounded-2xl border p-5 ${recClasses(rec.status)}`;
  recEl.innerHTML = `
    <p class="text-xs font-semibold uppercase tracking-wide">Smart farming recommendation</p>
    <h3 class="mt-2 text-lg font-semibold">${rec.title || "Recommendation"}</h3>
    <p class="mt-1 text-sm">${rec.msg || ""}</p>
  `;

  forecastBody.innerHTML = forecast.map((row) => `
    <tr class="border-t border-stone-100">
      <td class="px-4 py-3 text-sm text-emerald-950">${row["Date"] ?? "-"}</td>
      <td class="px-4 py-3 text-sm text-emerald-950">${Number(row["Max Temp (°C)"]).toFixed(1)}</td>
      <td class="px-4 py-3 text-sm text-emerald-950">${Number(row["Min Temp (°C)"]).toFixed(1)}</td>
      <td class="px-4 py-3 text-sm text-emerald-950">${Number(row["Rain Probability (%)"]).toFixed(0)}%</td>
    </tr>
  `).join("");

  renderCharts(forecast);
  resultEl.classList.remove("hidden");
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const city = cityInput.value.trim();
  if (!city) {
    showError("Please enter a city name.");
    return;
  }

  clearError();
  resultEl.classList.add("hidden");
  loadingEl.classList.remove("hidden");

  try {
    const data = await getWeather(city);
    renderWeather(data);
  } catch (err) {
    showError(err.message || "Weather data could not be retrieved.");
  } finally {
    loadingEl.classList.add("hidden");
  }
});

document.addEventListener("DOMContentLoaded", () => {
  if (navigator.geolocation) {
    navigator.geolocation.getCurrentPosition(
      async (position) => {
        const lat = position.coords.latitude;
        const lon = position.coords.longitude;
        try {
          const response = await fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lon}`);
          const data = await response.json();
          const city = data.address.city || data.address.town || data.address.village || data.address.county;
          if (city) {
            cityInput.value = city;
            form.dispatchEvent(new Event("submit", { cancelable: true, bubbles: true }));
          } else {
            fallbackIpLocation();
          }
        } catch (e) {
          fallbackIpLocation();
        }
      },
      (error) => {
        fallbackIpLocation();
      },
      { timeout: 5000 }
    );
  } else {
    fallbackIpLocation();
  }

  async function fallbackIpLocation() {
    try {
      const res = await fetch("https://ipapi.co/json/");
      if (res.ok) {
        const data = await res.json();
        if (data.city) {
          cityInput.value = data.city;
          form.dispatchEvent(new Event("submit", { cancelable: true, bubbles: true }));
        }
      }
    } catch (err) {
      console.error("Auto-location failed:", err);
    }
  }
});
