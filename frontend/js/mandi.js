import { getMandiPrices } from "./api.js";

const form = document.getElementById("mandi-form");
const stateEl = document.getElementById("state-select");
const cropEl = document.getElementById("crop-select");
const loadingEl = document.getElementById("mandi-loading");
const errorBox = document.getElementById("error-box");
const emptyBox = document.getElementById("empty-box");
const resultEl = document.getElementById("mandi-result");
const titleEl = document.getElementById("mandi-title");
const headEl = document.getElementById("mandi-head");
const bodyEl = document.getElementById("mandi-body");

function showError(message) {
  errorBox.textContent = message;
  errorBox.classList.remove("hidden");
}

function clearError() {
  errorBox.classList.add("hidden");
  errorBox.textContent = "";
}

function prettyHeader(key) {
  return key.replaceAll("_", " ");
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const state = stateEl.value;
  const crop = cropEl.value;

  clearError();
  emptyBox.classList.add("hidden");
  resultEl.classList.add("hidden");
  loadingEl.classList.remove("hidden");

  try {
    const data = await getMandiPrices(state, crop);
    if (data.empty || !data.records || data.records.length === 0) {
      emptyBox.textContent = data.message
        || "No recent market data found for this crop and state. Please try another combination.";
      emptyBox.classList.remove("hidden");
      return;
    }

    const columns = Object.keys(data.records[0]);
    titleEl.textContent = `Market Rates for ${data.crop} in ${data.state}`;
    headEl.innerHTML = `<tr>${columns.map((col) => `<th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-stone-500">${prettyHeader(col)}</th>`).join("")}</tr>`;
    bodyEl.innerHTML = data.records.map((row) => `
      <tr class="border-t border-stone-100">
        ${columns.map((col) => `<td class="px-4 py-3 text-sm text-emerald-950">${row[col] ?? ""}</td>`).join("")}
      </tr>
    `).join("");
    resultEl.classList.remove("hidden");
  } catch (err) {
    showError(err.message || "Market data could not be retrieved.");
  } finally {
    loadingEl.classList.add("hidden");
  }
});
