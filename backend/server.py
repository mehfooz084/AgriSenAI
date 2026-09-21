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

try:
    from backend import predict
except Exception as exc:
    predict = None
    print(f"Predict module unavailable: {exc}")

    
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
DISEASE_DB_PATH = os.path.join(BASE_DIR, "disease_database.json")

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP", "MPO"}
MAX_IMAGE_BYTES = 8 * 1024 * 1024

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="")
CORS(app)
app.config["MAX_CONTENT_LENGTH"] = MAX_IMAGE_BYTES + (512 * 1024)

model = None
model_error = None
disease_db = {}


def _json_safe(value):
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if isinstance(value, np.generic):
        return value.item()
    if hasattr(value, "item") and not isinstance(value, (bytes, str)):
        try:
            return value.item()
        except Exception:
            return value
    return value


def load_resources():
    global model, model_error, disease_db

    try:
        with open(DISEASE_DB_PATH, "r", encoding="utf-8") as f:
            disease_db = json.load(f)
    except FileNotFoundError:
        disease_db = {}

    if predict is None:
        model = None
        model_error = "TensorFlow/predict module is not available."
        print(model_error)
        return

    try:
        model = predict.load_model()
        model_error = None
    except Exception as exc:
        model = None
        model_error = str(exc)
        print(f"Failed to load model: {exc}")


load_resources()


def friendly_error(message, status=400):
    return jsonify({"error": message}), status


@app.errorhandler(413)
def too_large(_err):
    return friendly_error("The image is too large. Please upload a file under 8 MB.", 413)


@app.route("/")
def home():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/<page>.html")
def html_page(page):
    filename = f"{page}.html"
    target = os.path.join(FRONTEND_DIR, filename)
    if not os.path.isfile(target):
        return friendly_error("Page not found.", 404)
    return send_from_directory(FRONTEND_DIR, filename)


@app.get("/api/health")
def api_health():
    return jsonify({
        "status": "ok",
        "model_loaded": model is not None,
        "disease_db_loaded": bool(disease_db),
    })


@app.get("/api/diseases")
def api_diseases():
    if not disease_db:
        return friendly_error("Treatment database is unavailable.", 503)
    return jsonify({"diseases": list(disease_db.keys())})


@app.get("/api/treatment")
def api_treatment():
    key = (request.args.get("disease") or "").strip()
    if not key:
        return friendly_error("Please select a disease.")
    info = disease_db.get(key)
    if not info:
        return friendly_error("Disease information not found in the database.", 404)
    return jsonify({"key": key, "info": info})


@app.post("/api/predict")
def api_predict():
    if model is None:
        return friendly_error("The disease detection model is currently unavailable. Please try again later.", 503)

    if "image" not in request.files:
        return friendly_error("No image selected. Please choose a JPG or PNG leaf photo.")

    uploaded = request.files["image"]
    filename = secure_filename(uploaded.filename or "")
    if not filename:
        return friendly_error("No image selected. Please choose a JPG or PNG leaf photo.")

    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return friendly_error("Invalid image type. Only JPG, JPEG, and PNG files are allowed.")

    data = uploaded.read()
    if not data:
        return friendly_error("The uploaded file is empty. Please choose another image.")
    if len(data) > MAX_IMAGE_BYTES:
        return friendly_error("The image is too large. Please upload a file under 8 MB.", 413)

    try:
        with Image.open(BytesIO(data)) as img:
            img.verify()
            image_format = img.format
    except UnidentifiedImageError:
        return friendly_error("The file could not be read as an image. Please upload a valid JPG or PNG.")
    except Exception:
        return friendly_error("The file could not be read as an image. Please upload a valid JPG or PNG.")

    if image_format not in ALLOWED_FORMATS:
        return friendly_error("Invalid image type. Only JPG, JPEG, and PNG files are allowed.")

    image_file = BytesIO(data)
    image_file.name = filename
    image_file.seek(0)

    try:
        predicted_class, confidence = predict.predict_disease(image_file, model)
    except Exception:
        return friendly_error("Could not analyze the image. Please try another leaf photo.", 500)

    parts = predicted_class.split(" - ")
    plant_name = parts[0]
    disease_name = parts[1] if len(parts) > 1 else "Healthy"

    return jsonify({
        "predicted_class": predicted_class,
        "plant": plant_name,
        "disease": disease_name,
        "confidence": round(float(confidence), 2),
        "has_treatment": predicted_class in disease_db,
    })


@app.get("/api/weather")
def api_weather():
    city = (request.args.get("city") or "").strip()
    if not city:
        return friendly_error("Please enter a city name.")

    try:
        loc, cur, df_daily, rec, err = weather.fetch_weather_and_recommendations(city)
    except Exception:
        return friendly_error("Weather data could not be retrieved. Please try again.", 502)

    if err:
        if "not found" in err.lower():
            return friendly_error("City not found. Please check the spelling and try again.", 404)
        return friendly_error("Weather data could not be retrieved. Please try again.", 502)

    forecast = []
    if df_daily is not None and not df_daily.empty:
        records = df_daily.to_dict(orient="records")
        forecast = _json_safe(records)

    return jsonify({
        "location": _json_safe(loc),
        "current": _json_safe(cur),
        "recommendation": _json_safe(rec),
        "forecast": forecast,
    })


@app.get("/api/mandi")
def api_mandi():
    state = (request.args.get("state") or "").strip()
    crop = (request.args.get("crop") or "").strip()
    if not state or not crop:
        return friendly_error("Please select both a state and a crop.")

    try:
        df_mandi = mandi.get_mandi_prices(state, crop)
    except Exception:
        return friendly_error("Market data could not be retrieved. Please try again.", 502)

    if df_mandi is None or df_mandi.empty:
        return jsonify({
            "state": state,
            "crop": crop,
            "records": [],
            "empty": True,
            "message": "No recent market data found for this crop and state. Please try another combination.",
        })

    records = df_mandi.fillna("").astype(str).to_dict(orient="records")
    return jsonify({
        "state": state,
        "crop": crop,
        "records": records,
        "empty": False,
    })


@app.post("/api/chat")
def api_chat():
    req_data = request.get_json(silent=True) or {}
    message = req_data.get("message", "").strip()
    language = req_data.get("language", "Auto Detect")
    
    # Location data could contain latitude, longitude, and a resolved city/state
    location_data = {
        "city": req_data.get("location"),
        "state": req_data.get("state"),
        "lat": req_data.get("latitude"),
        "lon": req_data.get("longitude")
    }
    
    # Optional image context for disease explanation
    image_context = req_data.get("image_context")
    
    if not message:
        return friendly_error("Message cannot be empty.")
        
    reply, detected_lang = chatbot_service.get_chatbot_response(
        message=message, 
        language=language, 
        location_data=location_data,
        image_context=image_context
    )
    
    return jsonify({
        "success": True,
        "reply": reply,
        "language": detected_lang
    })

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
