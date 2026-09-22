const API_BASE = window.location.origin;
const LAST_DISEASE_KEY = "agrisense_last_disease";


// ============================================================
// DISEASE STORAGE
// ============================================================

export function setLastDisease(predictedClass) {
  if (predictedClass) {
    localStorage.setItem(
      LAST_DISEASE_KEY,
      predictedClass
    );
  }
}


export function getLastDisease() {
  return (
    localStorage.getItem(LAST_DISEASE_KEY) || ""
  );
}


// ============================================================
// PARSE RESPONSE
// ============================================================

async function parseResponse(response) {

  let payload = null;

  try {
    payload = await response.json();
  } catch (e) {
    payload = null;
  }


  console.log(
    "[AgriSense API]",
    response.status,
    response.url,
    payload
  );


  // ----------------------------------------------------------
  // HTTP ERROR
  // ----------------------------------------------------------

  if (!response.ok) {

    const message =
      payload && payload.error
        ? payload.error
        : `Server returned HTTP ${response.status}.`;

    const error = new Error(message);

    error.status = response.status;
    error.payload = payload;

    throw error;
  }


  // ----------------------------------------------------------
  // INVALID RESPONSE
  // ----------------------------------------------------------

  if (
    !payload ||
    typeof payload !== "object"
  ) {

    throw new Error(
      "The server returned an unexpected response."
    );
  }


  return payload;
}


// ============================================================
// GENERIC REQUEST
// ============================================================

async function request(
  path,
  options = {},
  timeoutMs = 30000
) {

  const controller =
    new AbortController();

  const timer = setTimeout(
    () => controller.abort(),
    timeoutMs
  );


  const url =
    `${API_BASE}${path}`;


  console.log(
    "[AgriSense API] REQUEST:",
    url
  );


  try {

    const response = await fetch(
      url,
      {
        ...options,

        signal:
          controller.signal,

        // Prevent browser/proxy caching
        cache: "no-store",

        headers: {
          ...(options.headers || {})
        }
      }
    );


    console.log(
      "[AgriSense API] RESPONSE:",
      response.status,
      response.statusText,
      url
    );


    return await parseResponse(
      response
    );

  } catch (err) {

    console.error(
      "[AgriSense API] ERROR:",
      err
    );


    // --------------------------------------------------------
    // REQUEST TIMEOUT
    // --------------------------------------------------------

    if (
      err.name === "AbortError"
    ) {

      throw new Error(
        "The request timed out. Please try again."
      );
    }


    // --------------------------------------------------------
    // HTTP ERROR
    // --------------------------------------------------------

    if (err.status) {

      throw err;
    }


    // --------------------------------------------------------
    // OFFLINE
    // --------------------------------------------------------

    if (
      !window.navigator.onLine
    ) {

      throw new Error(
        "You appear to be offline. Please check your connection."
      );
    }


    // --------------------------------------------------------
    // BROWSER / NETWORK ERROR
    // --------------------------------------------------------

    throw new Error(
      `Network error while contacting ${url}. ` +
      `Please check the browser console. ` +
      `Original error: ${err.message}`
    );

  } finally {

    clearTimeout(timer);
  }
}


// ============================================================
// DISEASE PREDICTION
// ============================================================

export async function predictDisease(
  file
) {

  const body =
    new FormData();

  body.append(
    "image",
    file
  );


  return request(
    "/api/predict",
    {
      method: "POST",
      body
    },
    90000
  );
}


// ============================================================
// DISEASES
// ============================================================

export async function getDiseases() {

  return request(
    "/api/diseases"
  );
}


// ============================================================
// TREATMENT
// ============================================================

export async function getTreatment(
  disease
) {

  const query =
    new URLSearchParams({
      disease
    });


  return request(
    `/api/treatment?${query.toString()}`
  );
}


// ============================================================
// WEATHER
// ============================================================

export async function getWeather(
  city
) {

  const query =
    new URLSearchParams({
      city
    });


  const path =
    `/api/weather?${query.toString()}`;


  console.log(
    "[AgriSense Weather] City:",
    city
  );

  console.log(
    "[AgriSense Weather] URL:",
    `${API_BASE}${path}`
  );


  return request(
    path,
    {
      method: "GET"
    },
    60000
  );
}


// ============================================================
// MANDI PRICES
// ============================================================

export async function getMandiPrices(
  state,
  crop
) {

  const query =
    new URLSearchParams({
      state,
      crop
    });


  return request(
    `/api/mandi?${query.toString()}`,
    {
      method: "GET"
    },
    60000
  );
}
