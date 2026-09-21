import json
import os
from io import BytesIO

from dotenv import load_dotenv

load_dotenv()

import numpy as np
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from PIL import Image, UnidentifiedImageError
from werkzeug.utils import secure_filename

from backend import mandi
from backend import weather
from backend import chatbot_service


# =========================================================
# PATHS
# =========================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

PROJECT_DIR = os.path.dirname(BASE_DIR)

FRONTEND_DIR = os.path.join(
    PROJECT_DIR,
    "frontend"
)

DISEASE_DB_PATH = os.path.join(
    PROJECT_DIR,
    "disease_database.json"
)


# =========================================================
# IMAGE SETTINGS
# =========================================================

ALLOWED_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp"
}

ALLOWED_FORMATS = {
    "JPEG",
    "PNG",
    "WEBP",
    "MPO"
}

MAX_IMAGE_BYTES = 8 * 1024 * 1024


# =========================================================
# FLASK APP
# =========================================================

app = Flask(
    __name__,
    static_folder=FRONTEND_DIR,
    static_url_path=""
)

CORS(app)

app.config["MAX_CONTENT_LENGTH"] = (
    MAX_IMAGE_BYTES + (512 * 1024)
)


# =========================================================
# GLOBAL RESOURCES
# =========================================================

# IMPORTANT:
# Model is NOT loaded when the server starts.
#
# It will only be loaded when /api/predict
# is called for the first time.

model = None
model_error = None

disease_db = {}


# =========================================================
# JSON SAFE CONVERTER
# =========================================================

def _json_safe(value):

    if isinstance(value, dict):
        return {
            k: _json_safe(v)
            for k, v in value.items()
        }

    if isinstance(value, (list, tuple)):
        return [
            _json_safe(v)
            for v in value
        ]

    if isinstance(value, np.generic):
        return value.item()

    if hasattr(value, "item") and not isinstance(
        value,
        (bytes, str)
    ):
        try:
            return value.item()
        except Exception:
            return value

    return value


# =========================================================
# LOAD NON-ML RESOURCES
# =========================================================

def load_resources():

    global disease_db

    try:

        with open(
            DISEASE_DB_PATH,
            "r",
            encoding="utf-8"
        ) as f:

            disease_db = json.load(f)

        print(
            "Disease database loaded successfully."
        )

    except FileNotFoundError:

        disease_db = {}

        print(
            "WARNING: disease_database.json not found."
        )

    except Exception as exc:

        disease_db = {}

        print(
            f"WARNING: Failed to load disease database: {exc}"
        )


# Load only the JSON database at startup.
#
# DO NOT load TensorFlow/model here.
load_resources()


# =========================================================
# LAZY MODEL LOADING
# =========================================================

def get_model():

    global model
    global model_error

    # If model is already loaded,
    # return it immediately.
    if model is not None:
        return model

    try:

        print("=" * 60)
        print("LOADING ML MODEL...")
        print("=" * 60)

        # IMPORTANT:
        # TensorFlow/predict is imported ONLY here.
        from backend import predict

        model = predict.load_model()

        model_error = None

        print("=" * 60)
        print("ML MODEL LOADED SUCCESSFULLY")
        print("=" * 60)

        return model

    except Exception as exc:

        model = None

        model_error = str(exc)

        print("=" * 60)
        print("MODEL LOAD ERROR")
        print("=" * 60)
        print(model_error)
        print("=" * 60)

        return None


# =========================================================
# ERROR HELPER
# =========================================================

def friendly_error(
    message,
    status=400
):

    return jsonify({
        "error": message
    }), status


# =========================================================
# FILE TOO LARGE
# =========================================================

@app.errorhandler(413)
def too_large(_err):

    return friendly_error(
        "The image is too large. Please upload a file under 8 MB.",
        413
    )


# =========================================================
# FRONTEND ROUTES
# =========================================================

@app.route("/")
def home():

    return send_from_directory(
        FRONTEND_DIR,
        "index.html"
    )


@app.route("/<page>.html")
def html_page(page):

    filename = f"{page}.html"

    target = os.path.join(
        FRONTEND_DIR,
        filename
    )

    if not os.path.isfile(target):

        return friendly_error(
            "Page not found.",
            404
        )

    return send_from_directory(
        FRONTEND_DIR,
        filename
    )


# =========================================================
# HEALTH CHECK
# =========================================================

@app.get("/api/health")
def api_health():

    return jsonify({

        "status": "ok",

        # FALSE at startup is NORMAL.
        #
        # It becomes TRUE after the first
        # successful disease prediction request.
        "model_loaded": model is not None,

        "disease_db_loaded": bool(disease_db)

    })


# =========================================================
# DISEASE LIST
# =========================================================

@app.get("/api/diseases")
def api_diseases():

    if not disease_db:

        return friendly_error(
            "Treatment database is unavailable.",
            503
        )

    return jsonify({
        "diseases": list(
            disease_db.keys()
        )
    })


# =========================================================
# TREATMENT
# =========================================================

@app.get("/api/treatment")
def api_treatment():

    key = (
        request.args.get("disease")
        or ""
    ).strip()

    if not key:

        return friendly_error(
            "Please select a disease."
        )

    info = disease_db.get(key)

    if not info:

        return friendly_error(
            "Disease information not found in the database.",
            404
        )

    return jsonify({

        "key": key,

        "info": info

    })


# =========================================================
# DISEASE PREDICTION
# =========================================================

@app.post("/api/predict")
def api_predict():

    # =====================================================
    # LAZY LOAD MODEL
    # =====================================================
    #
    # This is the important change.
    #
    # TensorFlow + MobileNetV2 will NOT load when
    # Gunicorn starts.
    #
    # It loads only when the user actually requests
    # disease prediction.
    #

    prediction_model = get_model()

    if prediction_model is None:

        return friendly_error(

            "The disease detection model is currently unavailable. "
            "Please try again later.",

            503
        )


    # =====================================================
    # CHECK IMAGE
    # =====================================================

    if "image" not in request.files:

        return friendly_error(
            "No image selected. Please choose a JPG or PNG leaf photo."
        )


    uploaded = request.files["image"]

    filename = secure_filename(
        uploaded.filename or ""
    )

    if not filename:

        return friendly_error(
            "No image selected. Please choose a JPG or PNG leaf photo."
        )


    # =====================================================
    # CHECK EXTENSION
    # =====================================================

    ext = os.path.splitext(
        filename
    )[1].lower()

    if ext not in ALLOWED_EXTENSIONS:

        return friendly_error(

            "Invalid image type. "
            "Only JPG, JPEG, PNG, and WEBP files are allowed."

        )


    # =====================================================
    # READ IMAGE
    # =====================================================

    data = uploaded.read()

    if not data:

        return friendly_error(
            "The uploaded file is empty. Please choose another image."
        )


    # =====================================================
    # CHECK IMAGE SIZE
    # =====================================================

    if len(data) > MAX_IMAGE_BYTES:

        return friendly_error(

            "The image is too large. "
            "Please upload a file under 8 MB.",

            413
        )


    # =====================================================
    # VERIFY IMAGE
    # =====================================================

    try:

        with Image.open(
            BytesIO(data)
        ) as img:

            img.verify()

            image_format = img.format

    except UnidentifiedImageError:

        return friendly_error(

            "The file could not be read as an image. "
            "Please upload a valid JPG, PNG, or WEBP image."

        )

    except Exception:

        return friendly_error(

            "The file could not be read as an image. "
            "Please upload a valid JPG, PNG, or WEBP image."

        )


    # =====================================================
    # CHECK REAL IMAGE FORMAT
    # =====================================================

    if image_format not in ALLOWED_FORMATS:

        return friendly_error(

            "Invalid image type. "
            "Only JPG, JPEG, PNG, and WEBP files are allowed."

        )


    # =====================================================
    # CREATE FILE OBJECT
    # =====================================================

    image_file = BytesIO(data)

    image_file.name = filename

    image_file.seek(0)


    # =====================================================
    # RUN MODEL PREDICTION
    # =====================================================

    try:

        # Import predict only when needed.
        from backend import predict

        predicted_class, confidence = (
            predict.predict_disease(
                image_file,
                prediction_model
            )
        )

    except Exception as exc:

        print(
            f"Prediction error: {exc}"
        )

        return friendly_error(

            "Could not analyze the image. "
            "Please try another leaf photo.",

            500
        )


    # =====================================================
    # SPLIT PLANT + DISEASE
    # =====================================================

    parts = predicted_class.split(
        " - "
    )

    plant_name = parts[0]

    disease_name = (
        parts[1]
        if len(parts) > 1
        else "Healthy"
    )


    # =====================================================
    # RESPONSE
    # =====================================================

    return jsonify({

        "predicted_class": predicted_class,

        "plant": plant_name,

        "disease": disease_name,

        "confidence": round(
            float(confidence),
            2
        ),

        "has_treatment": (
            predicted_class in disease_db
        )

    })


# =========================================================
# WEATHER
# =========================================================

@app.get("/api/weather")
def api_weather():

    city = (
        request.args.get("city")
        or ""
    ).strip()

    if not city:

        return friendly_error(
            "Please enter a city name."
        )


    try:

        (
            loc,
            cur,
            df_daily,
            rec,
            err
        ) = weather.fetch_weather_and_recommendations(
            city
        )

    except Exception as exc:

        print(
            f"Weather error: {exc}"
        )

        return friendly_error(

            "Weather data could not be retrieved. "
            "Please try again.",

            502
        )


    # =====================================================
    # WEATHER ERROR
    # =====================================================

    if err:

        if "not found" in err.lower():

            return friendly_error(

                "City not found. "
                "Please check the spelling and try again.",

                404
            )

        return friendly_error(

            "Weather data could not be retrieved. "
            "Please try again.",

            502
        )


    # =====================================================
    # FORECAST
    # =====================================================

    forecast = []

    if (
        df_daily is not None
        and not df_daily.empty
    ):

        records = (
            df_daily
            .to_dict(
                orient="records"
            )
        )

        forecast = _json_safe(
            records
        )


    # =====================================================
    # RESPONSE
    # =====================================================

    return jsonify({

        "location": _json_safe(
            loc
        ),

        "current": _json_safe(
            cur
        ),

        "recommendation": _json_safe(
            rec
        ),

        "forecast": forecast

    })


# =========================================================
# MANDI PRICES
# =========================================================

@app.get("/api/mandi")
def api_mandi():

    state = (
        request.args.get("state")
        or ""
    ).strip()

    crop = (
        request.args.get("crop")
        or ""
    ).strip()


    if not state or not crop:

        return friendly_error(

            "Please select both a state and a crop."

        )


    # =====================================================
    # FETCH MARKET DATA
    # =====================================================

    try:

        df_mandi = mandi.get_mandi_prices(
            state,
            crop
        )

    except Exception as exc:

        print(
            f"Mandi error: {exc}"
        )

        return friendly_error(

            "Market data could not be retrieved. "
            "Please try again.",

            502
        )


    # =====================================================
    # NO DATA
    # =====================================================

    if (
        df_mandi is None
        or df_mandi.empty
    ):

        return jsonify({

            "state": state,

            "crop": crop,

            "records": [],

            "empty": True,

            "message":
                "No recent market data found "
                "for this crop and state. "
                "Please try another combination."

        })


    # =====================================================
    # CONVERT DATAFRAME
    # =====================================================

    records = (
        df_mandi
        .fillna("")
        .astype(str)
        .to_dict(
            orient="records"
        )
    )


    # =====================================================
    # RESPONSE
    # =====================================================

    return jsonify({

        "state": state,

        "crop": crop,

        "records": records,

        "empty": False

    })


# =========================================================
# CHATBOT
# =========================================================

@app.post("/api/chat")
def api_chat():

    req_data = (
        request.get_json(
            silent=True
        )
        or {}
    )


    # =====================================================
    # MESSAGE
    # =====================================================

    message = (
        req_data.get(
            "message",
            ""
        )
        .strip()
    )


    # =====================================================
    # LANGUAGE
    # =====================================================

    language = req_data.get(
        "language",
        "Auto Detect"
    )


    # =====================================================
    # LOCATION DATA
    # =====================================================

    location_data = {

        "city": req_data.get(
            "location"
        ),

        "state": req_data.get(
            "state"
        ),

        "lat": req_data.get(
            "latitude"
        ),

        "lon": req_data.get(
            "longitude"
        )

    }


    # =====================================================
    # IMAGE CONTEXT
    # =====================================================

    image_context = req_data.get(
        "image_context"
    )


    # =====================================================
    # EMPTY MESSAGE
    # =====================================================

    if not message:

        return friendly_error(
            "Message cannot be empty."
        )


    # =====================================================
    # CHATBOT RESPONSE
    # =====================================================

    try:

        (
            reply,
            detected_lang
        ) = chatbot_service.get_chatbot_response(

            message=message,

            language=language,

            location_data=location_data,

            image_context=image_context

        )

    except Exception as exc:

        print(
            f"Chatbot error: {exc}"
        )

        return friendly_error(

            "The AI assistant is currently unavailable. "
            "Please try again later.",

            502
        )


    # =====================================================
    # RESPONSE
    # =====================================================

    return jsonify({

        "success": True,

        "reply": reply,

        "language": detected_lang

    })


# =========================================================
# LOCAL DEVELOPMENT
# =========================================================

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            5000
        )
    )

    app.run(

        host="0.0.0.0",

        port=port,

        debug=False

    )
