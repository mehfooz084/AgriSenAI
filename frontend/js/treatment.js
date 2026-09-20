import { getDiseases, getLastDisease, getTreatment } from "./api.js";

const selectEl = document.getElementById("disease-select");
const loadingEl = document.getElementById("treatment-loading");
const errorBox = document.getElementById("error-box");
const emptyBox = document.getElementById("empty-box");
const resultEl = document.getElementById("treatment-result");
const titleEl = document.getElementById("treatment-title");
const healthyCard = document.getElementById("healthy-card");
const optionsEl = document.getElementById("treatment-options");

function showError(message) {
  errorBox.textContent = message;
  errorBox.classList.remove("hidden");
}

function clearError() {
  errorBox.classList.add("hidden");
  errorBox.textContent = "";
}

function requestedDisease() {
  const params = new URLSearchParams(window.location.search);
  return params.get("disease") || getLastDisease() || "";
}

function renderTreatment(key, info) {
  emptyBox.classList.add("hidden");
  resultEl.classList.remove("hidden");
  titleEl.textContent = `Treatment Plan for ${info.disease} (${info.plant})`;

  if (info.status === "Healthy") {
    healthyCard.classList.remove("hidden");
    optionsEl.innerHTML = "";
    optionsEl.classList.add("hidden");
    return;
  }

  healthyCard.classList.add("hidden");
  optionsEl.classList.remove("hidden");
  const treatments = Array.isArray(info.treatment) ? info.treatment : [];
  optionsEl.innerHTML = treatments.map((item, index) => `
    <article class="rounded-2xl border border-stone-200 bg-white p-5 shadow-sm">
      <p class="text-xs font-semibold uppercase tracking-wide text-emerald-700">Treatment option ${index + 1}</p>
      <h3 class="mt-1 text-lg font-semibold text-emerald-950">${item.medicine || "Not specified"}</h3>
      <dl class="mt-4 grid gap-3 sm:grid-cols-2">
        <div class="rounded-xl bg-emerald-50 p-3">
          <dt class="text-xs uppercase tracking-wide text-emerald-700">Medicine</dt>
          <dd class="mt-1 text-sm text-emerald-950">${item.medicine || "-"}</dd>
        </div>
        <div class="rounded-xl bg-amber-50 p-3">
          <dt class="text-xs uppercase tracking-wide text-amber-700">Dosage</dt>
          <dd class="mt-1 text-sm text-emerald-950">${item.dosage || "-"}</dd>
        </div>
        <div class="rounded-xl bg-stone-50 p-3 sm:col-span-2">
          <dt class="text-xs uppercase tracking-wide text-stone-500">Source / Advisory</dt>
          <dd class="mt-1 text-sm text-emerald-950">${item.source || "-"}</dd>
        </div>
        <div class="rounded-xl bg-sky-50 p-3 sm:col-span-2">
          <dt class="text-xs uppercase tracking-wide text-sky-700">Special note</dt>
          <dd class="mt-1 text-sm text-emerald-950">${item.note || "-"}</dd>
        </div>
      </dl>
    </article>
  `).join("");
}

async function loadSelected() {
  const key = selectEl.value;
  if (!key) return;

  clearError();
  resultEl.classList.add("hidden");
  loadingEl.classList.remove("hidden");

  try {
    const data = await getTreatment(key);
    renderTreatment(data.key, data.info);
  } catch (err) {
    showError(err.message || "Disease information not found in the database.");
  } finally {
    loadingEl.classList.add("hidden");
  }
}

async function init() {
  loadingEl.classList.remove("hidden");
  try {
    const data = await getDiseases();
    const diseases = data.diseases || [];
    if (!diseases.length) {
      showError("Treatment database is unavailable.");
      return;
    }

    const preferred = requestedDisease();
    if (preferred) {
      const dropdownContainer = document.getElementById("dropdown-container");
      if (dropdownContainer) dropdownContainer.classList.add("hidden");
    }

    selectEl.innerHTML = diseases.map((name) => {
      const selected = name === preferred ? "selected" : "";
      return `<option value="${name}" ${selected}>${name}</option>`;
    }).join("");

    if (preferred && !diseases.includes(preferred)) {
      showError("Disease information not found in the database.");
      return;
    }

    await loadSelected();
  } catch (err) {
    showError(err.message || "Could not load treatment information.");
  } finally {
    loadingEl.classList.add("hidden");
  }
}

selectEl.addEventListener("change", loadSelected);
init();
