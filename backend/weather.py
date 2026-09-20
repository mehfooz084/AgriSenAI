import openmeteo_requests
import requests
import requests_cache
import pandas as pd
from retry_requests import retry

def fetch_weather_and_recommendations(city):
    """Fetches weather data and generates farming recommendations."""
    geo = requests.get(
        "https://geocoding-api.open-meteo.com/v1/search",
        params={"name": city, "count": 1},
        timeout=20
    ).json()

    if "results" not in geo:
        return None, None, None, None, "City not found!"

    r = geo["results"][0]
    lat, lon = r["latitude"], r["longitude"]
    location_details = {
        "city": city.title(),
        "state": r.get("admin1", "N/A"),
        "country": r.get("country", "N/A"),
        "lat": lat,
        "lon": lon
    }

    cache = requests_cache.CachedSession(".cache", expire_after=3600)
    client = openmeteo_requests.Client(session=retry(cache, retries=5, backoff_factor=0.2))

    params = {
        "latitude": lat,
        "longitude": lon,
        "models": "ncep_gfs_seamless",
        "current": ["temperature_2m", "relative_humidity_2m", "wind_speed_10m"],
        "hourly": ["temperature_2m", "relative_humidity_2m", "precipitation_probability", "wind_speed_10m"],
        "daily": ["temperature_2m_max", "temperature_2m_min", "precipitation_probability_max"],
        "forecast_days": 16,
        "timezone": "auto"
    }

    try:
        resp = client.weather_api("https://api.open-meteo.com/v1/forecast", params=params)[0]
    except Exception as e:
        return None, None, None, None, f"API Error: {str(e)}"

    cur = resp.Current()
    current_weather = {
        "temp": cur.Variables(0).Value(),
        "hum": cur.Variables(1).Value(),
        "wind": cur.Variables(2).Value()
    }

    daily = resp.Daily()
    daily_df = pd.DataFrame({
        "Date": pd.date_range(
            start=pd.to_datetime(daily.Time(), unit="s"),
            periods=len(daily.Variables(0).ValuesAsNumpy()),
            freq="D"
        ),
        "Max Temp (°C)": daily.Variables(0).ValuesAsNumpy(),
        "Min Temp (°C)": daily.Variables(1).ValuesAsNumpy(),
        "Rain Probability (%)": daily.Variables(2).ValuesAsNumpy()
    })
    daily_df["Date"] = daily_df["Date"].dt.strftime("%d-%b-%Y")

    rain3 = max(daily.Variables(2).ValuesAsNumpy()[:3])
    
    if rain3 >= 60:
        rec, reason = "🌧 Delay Spraying", f"Rain expected within next 3 days (Max {rain3:.0f}%)."
        status = "error"
    elif current_weather["wind"] >= 20:
        rec, reason = "💨 Avoid Spraying", f"Wind speed {current_weather['wind']:.1f} km/h."
        status = "warning"
    elif current_weather["temp"] >= 35:
        rec, reason = "☀️ Spray in Evening", f"Temperature {current_weather['temp']:.1f}°C."
        status = "warning"
    elif current_weather["hum"] >= 85:
        rec, reason = "💧 Monitor Crop", "High humidity may increase fungal disease risk."
        status = "warning"
    else:
        rec, reason = "✅ Safe to Spray", "Weather conditions are suitable."
        status = "success"

    recommendation = {"status": status, "title": rec, "msg": reason}

    return location_details, current_weather, daily_df, recommendation, None