import { predictDisease, setLastDisease } from "./api.js";

const ALLOWED_TYPES = ["image/jpeg", "image/png", "image/webp"];
const ALLOWED_EXT = [".jpg", ".jpeg", ".png", ".webp"];
const MAX_BYTES = 8 * 1024 * 1024;
const LOADING_MESSAGES = [
  "AI is analyzing the leaf...",
  "Extracting visual features...",
  "Running disease detection model...",
  "Generating results...",
];

const fileInput = document.getElementById("leaf-input");
const dropzone = document.getElementById("dropzone");
const previewWrap = document.getElementById("preview-wrap");
const previewImage = document.getElementById("preview-image");
const analyzeBtn = document.getElementById("analyze-btn");
const loadingCard = document.getElementById("loading-card");
const loadingText = document.getElementById("loading-text");
const resultCard = document.getElementById("result-card");
const errorBox = document.getElementById("error-box");
const plantNameEl = document.getElementById("plant-name");
const diseaseNameEl = document.getElementById("disease-name");
const confidenceValueEl = document.getElementById("confidence-value");
const confidenceBarEl = document.getElementById("confidence-bar");
const treatmentLink = document.getElementById("treatment-link");
const fileNameEl = document.getElementById("file-name");

let selectedFile = null;
let loadingTimer = null;

function showError(message) {
  errorBox.textContent = message;
  errorBox.classList.remove("hidden");
}

function clearError() {
  errorBox.classList.add("hidden");
  errorBox.textContent = "";
}

function isAllowedFile(file) {
  const name = (file.name || "").toLowerCase();
  const extOk = ALLOWED_EXT.some((ext) => name.endsWith(ext));
  const typeOk = !file.type || ALLOWED_TYPES.includes(file.type);
  return extOk && typeOk;
}

function setFile(file) {
  clearError();
  resultCard.classList.add("hidden");
  loadingCard.classList.add("hidden");

  if (!file) {
    selectedFile = null;
    previewWrap.classList.add("hidden");
    analyzeBtn.disabled = true;
    fileNameEl.textContent = "JPG, JPEG, or PNG up to 8 MB";
    return;
  }

  if (!isAllowedFile(file)) {
    selectedFile = null;
    previewWrap.classList.add("hidden");
    analyzeBtn.disabled = true;
    showError("Invalid image. Please upload a JPG, JPEG, or PNG file.");
    return;
  }

  if (file.size > MAX_BYTES) {
    selectedFile = null;
    previewWrap.classList.add("hidden");
    analyzeBtn.disabled = true;
    showError("The image is too large. Please upload a file under 8 MB.");
    return;
  }

  selectedFile = file;
  fileNameEl.textContent = file.name;
  previewImage.src = URL.createObjectURL(file);
  previewWrap.classList.remove("hidden");
  analyzeBtn.disabled = false;
}

function startLoadingCopy() {
  let index = 0;
  loadingText.textContent = LOADING_MESSAGES[0];
  loadingTimer = setInterval(() => {
    index = (index + 1) % LOADING_MESSAGES.length;
    loadingText.textContent = LOADING_MESSAGES[index];
  }, 1400);
}

function stopLoadingCopy() {
  if (loadingTimer) {
    clearInterval(loadingTimer);
    loadingTimer = null;
  }
}

async function analyzeImage() {
  if (!selectedFile) {
    showError("Please select a leaf image first.");
    return;
  }

  clearError();
  resultCard.classList.add("hidden");
  loadingCard.classList.remove("hidden");
  analyzeBtn.disabled = true;
  startLoadingCopy();

  try {
    const result = await predictDisease(selectedFile);
    if (!result.predicted_class || typeof result.confidence !== "number") {
      throw new Error("The server returned an unexpected response.");
    }

    plantNameEl.textContent = result.plant;
    diseaseNameEl.textContent = result.disease;
    confidenceValueEl.textContent = `${result.confidence.toFixed(2)}%`;
    confidenceBarEl.style.width = `${Math.max(0, Math.min(100, result.confidence))}%`;

    setLastDisease(result.predicted_class);
    treatmentLink.href = `treatment.html?disease=${encodeURIComponent(result.predicted_class)}`;

    resultCard.classList.remove("hidden");
  } catch (err) {
    showError(err.message || "Could not analyze the image. Please try again.");
  } finally {
    stopLoadingCopy();
    loadingCard.classList.add("hidden");
    analyzeBtn.disabled = !selectedFile;
  }
}

fileInput.addEventListener("change", (event) => {
  const file = event.target.files && event.target.files[0];
  setFile(file || null);
});

["dragenter", "dragover"].forEach((name) => {
  dropzone.addEventListener(name, (event) => {
    event.preventDefault();
    dropzone.classList.add("is-active");
  });
});

["dragleave", "drop"].forEach((name) => {
  dropzone.addEventListener(name, (event) => {
    event.preventDefault();
    dropzone.classList.remove("is-active");
  });
});

dropzone.addEventListener("drop", (event) => {
  const file = event.dataTransfer.files && event.dataTransfer.files[0];
  if (file) {
    fileInput.files = event.dataTransfer.files;
    setFile(file);
  }
});

analyzeBtn.addEventListener("click", analyzeImage);
