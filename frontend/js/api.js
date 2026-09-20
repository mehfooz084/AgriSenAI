const API_BASE = "";
const LAST_DISEASE_KEY = "agrisense_last_disease";

export function setLastDisease(predictedClass) {
  if (predictedClass) {
    localStorage.setItem(LAST_DISEASE_KEY, predictedClass);
  }
}

export function getLastDisease() {
  return localStorage.getItem(LAST_DISEASE_KEY) || "";
}

async function parseResponse(response) {
  let payload = null;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }

  if (!response.ok) {
    const message = payload && payload.error
      ? payload.error
      : "Something went wrong. Please try again.";
    const error = new Error(message);
    error.status = response.status;
    throw error;
  }

  if (!payload || typeof payload !== "object") {
    throw new Error("The server returned an unexpected response.");
  }

  return payload;
}

async function request(path, options = {}, timeoutMs = 30000) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(`${API_BASE}${path}`, {
      ...options,
      signal: controller.signal,
    });
    return await parseResponse(response);
  } catch (err) {
    if (err.name === "AbortError") {
      throw new Error("The request timed out. Please try again.");
    }
    if (err.status) {
      throw err;
    }
    if (!window.navigator.onLine) {
      throw new Error("You appear to be offline. Please check your connection.");
    }
    throw new Error("Backend unavailable. Start the AgriSense AI server and try again.");
  } finally {
    clearTimeout(timer);
  }
}

export async function predictDisease(file) {
  const body = new FormData();
  body.append("image", file);
  return request("/api/predict", { method: "POST", body }, 90000);
}

export async function getDiseases() {
  return request("/api/diseases");
}

export async function getTreatment(disease) {
  const query = new URLSearchParams({ disease });
  return request(`/api/treatment?${query.toString()}`);
}

export async function getWeather(city) {
  const query = new URLSearchParams({ city });
  return request(`/api/weather?${query.toString()}`, {}, 45000);
}

export async function getMandiPrices(state, crop) {
  const query = new URLSearchParams({ state, crop });
  return request(`/api/mandi?${query.toString()}`, {}, 45000);
}
