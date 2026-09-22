import openmeteo_requests
import requests
import pandas as pd
from retry_requests import retry


def fetch_weather_and_recommendations(city):
    """
    Fetch live weather data from Open-Meteo
    and generate farming recommendations.

    Vercel-compatible version:
    No local SQLite/cache is used.
    """

    # =========================================================
    # 1. GEOCODING
    # =========================================================

    try:
        geo_response = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={
                "name": city,
                "count": 1
            },
            timeout=20
        )

        geo_response.raise_for_status()
        geo = geo_response.json()

    except Exception as e:

        print("=" * 60)
        print("GEOCODING ERROR")
        print("City:", city)
        print("Error:", str(e))
        print("=" * 60)

        return (
            None,
            None,
            None,
            None,
            f"Geocoding Error: {str(e)}"
        )

    # =========================================================
    # 2. CITY NOT FOUND
    # =========================================================

    if "results" not in geo or not geo["results"]:

        return (
            None,
            None,
            None,
            None,
            "City not found!"
        )

    # =========================================================
    # 3. LOCATION DETAILS
    # =========================================================

    r = geo["results"][0]

    lat = r["latitude"]
    lon = r["longitude"]

    location_details = {
        "city": r.get("name", city.title()),
        "state": r.get("admin1", "N/A"),
        "country": r.get("country", "N/A"),
        "lat": lat,
        "lon": lon
    }

    print("=" * 60)
    print("WEATHER LOCATION")
    print("City:", location_details["city"])
    print("State:", location_details["state"])
    print("Country:", location_details["country"])
    print("Latitude:", lat)
    print("Longitude:", lon)
    print("=" * 60)

    # =========================================================
    # 4. OPEN-METEO CLIENT
    # =========================================================

    try:

        # IMPORTANT:
        # No requests_cache here.
        # This avoids SQLite filesystem errors on Vercel.

        session = requests.Session()

        retry_session = retry(
            session,
            retries=3,
            backoff_factor=0.2
        )

        client = openmeteo_requests.Client(
            session=retry_session
        )

        # =====================================================
        # 5. WEATHER PARAMETERS
        # =====================================================

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

        # =====================================================
        # 6. API REQUEST
        # =====================================================

        responses = client.weather_api(
            "https://api.open-meteo.com/v1/forecast",
            params=params
        )

        resp = responses[0]

    except Exception as e:

        print("=" * 60)
        print("OPEN-METEO API ERROR")
        print("Error type:", type(e).__name__)
        print("Error:", str(e))
        print("=" * 60)

        return (
            None,
            None,
            None,
            None,
            f"Weather API Error: {str(e)}"
        )

    # =========================================================
    # 7. CURRENT WEATHER
    # =========================================================

    try:

        cur = resp.Current()

        current_weather = {
            "temp": cur.Variables(0).Value(),
            "hum": cur.Variables(1).Value(),
            "wind": cur.Variables(2).Value()
        }

        print("=" * 60)
        print("CURRENT WEATHER")
        print("Temperature:", current_weather["temp"])
        print("Humidity:", current_weather["hum"])
        print("Wind:", current_weather["wind"])
        print("=" * 60)

    except Exception as e:

        print("=" * 60)
        print("CURRENT WEATHER PARSING ERROR")
        print("Error:", str(e))
        print("=" * 60)

        return (
            None,
            None,
            None,
            None,
            f"Weather Data Error: {str(e)}"
        )

    # =========================================================
    # 8. DAILY FORECAST
    # =========================================================

    try:

        daily = resp.Daily()

        max_temp = daily.Variables(0).ValuesAsNumpy()
        min_temp = daily.Variables(1).ValuesAsNumpy()
        rain_probability = daily.Variables(2).ValuesAsNumpy()

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

            "Rain Probability (%)": rain_probability
        })

        daily_df["Date"] = (
            daily_df["Date"]
            .dt.strftime("%d-%b-%Y")
        )

    except Exception as e:

        print("=" * 60)
        print("DAILY WEATHER PARSING ERROR")
        print("Error:", str(e))
        print("=" * 60)

        return (
            location_details,
            current_weather,
            None,
            None,
            f"Forecast Data Error: {str(e)}"
        )

    # =========================================================
    # 9. FARMING RECOMMENDATION
    # =========================================================

    rain3 = max(
        rain_probability[:3]
    )

    wind = current_weather["wind"]
    temp = current_weather["temp"]
    humidity = current_weather["hum"]

    if rain3 >= 60:

        rec = "🌧 Delay Spraying"

        reason = (
            f"Rain expected within next 3 days "
            f"(Max {rain3:.0f}%)."
        )

        status = "error"

    elif wind >= 20:

        rec = "💨 Avoid Spraying"

        reason = (
            f"Wind speed is "
            f"{wind:.1f} km/h."
        )

        status = "warning"

    elif temp >= 35:

        rec = "☀️ Spray in Evening"

        reason = (
            f"Temperature is "
            f"{temp:.1f}°C."
        )

        status = "warning"

    elif humidity >= 85:

        rec = "💧 Monitor Crop"

        reason = (
            "High humidity may increase "
            "fungal disease risk."
        )

        status = "warning"

    else:

        rec = "✅ Safe to Spray"

        reason = (
            "Weather conditions are "
            "suitable."
        )

        status = "success"

    recommendation = {
        "status": status,
        "title": rec,
        "msg": reason
    }

    # =========================================================
    # 10. DEBUG OUTPUT
    # =========================================================

    print("=" * 60)
    print("WEATHER FETCH SUCCESS")
    print("City:", location_details["city"])
    print("Temperature:", current_weather["temp"])
    print("Humidity:", current_weather["hum"])
    print("Wind:", current_weather["wind"])
    print("3-Day Max Rain Probability:", rain3)
    print("Recommendation:", rec)
    print("=" * 60)

    # =========================================================
    # 11. RETURN EVERYTHING
    # =========================================================

    return (
        location_details,
        current_weather,
        daily_df,
        recommendation,
        None
    )
