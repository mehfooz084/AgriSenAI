import openmeteo_requests
import requests
import pandas as pd
from retry_requests import retry


# ============================================================
# GEOCODING
# ============================================================

def get_coordinates(city):
    """
    Get latitude/longitude for a city.

    Primary:
        Open-Meteo Geocoding

    Fallback:
        Nominatim / OpenStreetMap
    """

    # --------------------------------------------------------
    # PRIMARY: OPEN-METEO
    # --------------------------------------------------------

    try:

        print("=" * 60)
        print("GEOCODING WITH OPEN-METEO")
        print("City:", city)
        print("=" * 60)

        response = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={
                "name": city,
                "count": 1,
                "language": "en",
                "format": "json"
            },
            timeout=12
        )

        response.raise_for_status()

        geo = response.json()

        if geo.get("results"):

            result = geo["results"][0]

            print("Open-Meteo geocoding successful.")

            return {
                "city": result.get("name", city.title()),
                "state": result.get("admin1", "N/A"),
                "country": result.get("country", "N/A"),
                "lat": result["latitude"],
                "lon": result["longitude"]
            }

        print("Open-Meteo returned no results.")

    except Exception as e:

        print("=" * 60)
        print("OPEN-METEO GEOCODING FAILED")
        print("Error type:", type(e).__name__)
        print("Error:", str(e))
        print("Trying Nominatim fallback...")
        print("=" * 60)

    # --------------------------------------------------------
    # FALLBACK: NOMINATIM
    # --------------------------------------------------------

    try:

        print("=" * 60)
        print("GEOCODING WITH NOMINATIM")
        print("City:", city)
        print("=" * 60)

        response = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={
                "q": city,
                "format": "json",
                "limit": 1
            },
            headers={
                "User-Agent": "AgriSenseAI/1.0"
            },
            timeout=12
        )

        response.raise_for_status()

        results = response.json()

        if results:

            result = results[0]

            lat = float(result["lat"])
            lon = float(result["lon"])

            address = result.get("address", {})

            print("Nominatim geocoding successful.")
            print("Latitude:", lat)
            print("Longitude:", lon)

            return {
                "city": (
                    address.get("city")
                    or address.get("town")
                    or address.get("village")
                    or city.title()
                ),
                "state": address.get(
                    "state",
                    "N/A"
                ),
                "country": address.get(
                    "country",
                    "N/A"
                ),
                "lat": lat,
                "lon": lon
            }

        print("Nominatim returned no results.")

    except Exception as e:

        print("=" * 60)
        print("NOMINATIM GEOCODING FAILED")
        print("Error type:", type(e).__name__)
        print("Error:", str(e))
        print("=" * 60)

    return None


# ============================================================
# WEATHER FUNCTION
# ============================================================

def fetch_weather_and_recommendations(city):
    """
    Fetch live weather data and generate
    farming recommendations.
    """

    # ========================================================
    # 1. GET COORDINATES
    # ========================================================

    location_details = get_coordinates(city)

    if not location_details:

        return (
            None,
            None,
            None,
            None,
            f"Could not find weather location for {city}."
        )

    lat = location_details["lat"]
    lon = location_details["lon"]

    print("=" * 60)
    print("LOCATION FOUND")
    print("City:", location_details["city"])
    print("State:", location_details["state"])
    print("Country:", location_details["country"])
    print("Latitude:", lat)
    print("Longitude:", lon)
    print("=" * 60)

    # ========================================================
    # 2. OPEN-METEO WEATHER CLIENT
    # ========================================================

    try:

        session = requests.Session()

        retry_session = retry(
            session,
            retries=3,
            backoff_factor=0.5
        )

        client = openmeteo_requests.Client(
            session=retry_session
        )

        # ====================================================
        # WEATHER PARAMETERS
        # ====================================================

        params = {
            "latitude": lat,
            "longitude": lon,

            "models": "ncep_gfs_seamless",

            "current": [
                "temperature_2m",
                "relative_humidity_2m",
                "wind_speed_10m"
            ],

            "hourly": [
                "temperature_2m",
                "relative_humidity_2m",
                "precipitation_probability",
                "wind_speed_10m"
            ],

            "daily": [
                "temperature_2m_max",
                "temperature_2m_min",
                "precipitation_probability_max"
            ],

            "forecast_days": 16,

            "timezone": "auto"
        }

        # ====================================================
        # CALL OPEN-METEO
        # ====================================================

        print("=" * 60)
        print("REQUESTING WEATHER DATA...")
        print("=" * 60)

        responses = client.weather_api(
            "https://api.open-meteo.com/v1/forecast",
            params=params
        )

        resp = responses[0]

        print("Weather API request successful.")

    except Exception as e:

        print("=" * 60)
        print("OPEN-METEO WEATHER API ERROR")
        print("Error type:", type(e).__name__)
        print("Error:", str(e))
        print("=" * 60)

        return (
            location_details,
            None,
            None,
            None,
            f"Weather API Error: {str(e)}"
        )

    # ========================================================
    # 3. CURRENT WEATHER
    # ========================================================

    try:

        current = resp.Current()

        current_weather = {
            "temp": current.Variables(0).Value(),
            "hum": current.Variables(1).Value(),
            "wind": current.Variables(2).Value()
        }

        print("=" * 60)
        print("CURRENT WEATHER")
        print("=" * 60)

        print(
            "Temperature:",
            current_weather["temp"],
            "°C"
        )

        print(
            "Humidity:",
            current_weather["hum"],
            "%"
        )

        print(
            "Wind:",
            current_weather["wind"],
            "km/h"
        )

        print("=" * 60)

    except Exception as e:

        print("=" * 60)
        print("CURRENT WEATHER PARSING ERROR")
        print("Error:", str(e))
        print("=" * 60)

        return (
            location_details,
            None,
            None,
            None,
            f"Weather Data Error: {str(e)}"
        )

    # ========================================================
    # 4. DAILY FORECAST
    # ========================================================

    try:

        daily = resp.Daily()

        max_temp = (
            daily
            .Variables(0)
            .ValuesAsNumpy()
        )

        min_temp = (
            daily
            .Variables(1)
            .ValuesAsNumpy()
        )

        rain_probability = (
            daily
            .Variables(2)
            .ValuesAsNumpy()
        )

        daily_df = pd.DataFrame({

            "Date": pd.date_range(
                start=pd.to_datetime(
                    daily.Time(),
                    unit="s"
                ),
                periods=len(max_temp),
                freq="D"
            ),

            "Max Temp (°C)": max_temp,

            "Min Temp (°C)": min_temp,

            "Rain Probability (%)":
                rain_probability
        })

        daily_df["Date"] = (
            daily_df["Date"]
            .dt.strftime("%d-%b-%Y")
        )

    except Exception as e:

        print("=" * 60)
        print("DAILY FORECAST ERROR")
        print("Error:", str(e))
        print("=" * 60)

        return (
            location_details,
            current_weather,
            None,
            None,
            f"Forecast Data Error: {str(e)}"
        )

    # ========================================================
    # 5. FARMING RECOMMENDATION
    # ========================================================

    rain3 = max(
        rain_probability[:3]
    )

    temp = current_weather["temp"]
    humidity = current_weather["hum"]
    wind = current_weather["wind"]

    # --------------------------------------------------------
    # HIGH RAIN
    # --------------------------------------------------------

    if rain3 >= 60:

        rec = "🌧 Delay Spraying"

        reason = (
            f"Rain expected within the next "
            f"3 days (maximum probability "
            f"{rain3:.0f}%)."
        )

        status = "error"

    # --------------------------------------------------------
    # HIGH WIND
    # --------------------------------------------------------

    elif wind >= 20:

        rec = "💨 Avoid Spraying"

        reason = (
            f"Wind speed is "
            f"{wind:.1f} km/h."
        )

        status = "warning"

    # --------------------------------------------------------
    # HIGH TEMPERATURE
    # --------------------------------------------------------

    elif temp >= 35:

        rec = "☀️ Spray in Evening"

        reason = (
            f"Temperature is "
            f"{temp:.1f}°C."
        )

        status = "warning"

    # --------------------------------------------------------
    # HIGH HUMIDITY
    # --------------------------------------------------------

    elif humidity >= 85:

        rec = "💧 Monitor Crop"

        reason = (
            "High humidity may increase "
            "fungal disease risk."
        )

        status = "warning"

    # --------------------------------------------------------
    # GOOD WEATHER
    # --------------------------------------------------------

    else:

        rec = "✅ Safe to Spray"

        reason = (
            "Weather conditions are "
            "suitable for spraying."
        )

        status = "success"

    recommendation = {
        "status": status,
        "title": rec,
        "msg": reason
    }

    # ========================================================
    # 6. FINAL DEBUG
    # ========================================================

    print("=" * 60)
    print("WEATHER FETCH SUCCESS")
    print("=" * 60)

    print(
        "City:",
        location_details["city"]
    )

    print(
        "Temperature:",
        current_weather["temp"]
    )

    print(
        "Humidity:",
        current_weather["hum"]
    )

    print(
        "Wind:",
        current_weather["wind"]
    )

    print(
        "3-Day Rain Probability:",
        rain3
    )

    print(
        "Recommendation:",
        rec
    )

    print("=" * 60)

    # ========================================================
    # 7. RETURN
    # ========================================================

    return (
        location_details,
        current_weather,
        daily_df,
        recommendation,
        None
    )
