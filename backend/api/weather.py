# api/weather.py
from flask import Blueprint, request, jsonify, current_app
import os
import requests
from datetime import datetime

bp = Blueprint("weather", __name__, url_prefix="/api")

OPENWEATHER_GEOCODE = "http://api.openweathermap.org/geo/1.0/direct"
OPENWEATHER_ONECALL = "https://api.openweathermap.org/data/2.5/onecall"

# Demo fixed feature set (a simple, deterministic sample used for demo/presentation)
DEMO_FEATURES = {
    "MinTemp": 18.0,
    "MaxTemp": 30.0,
    "Rainfall": 0.0,
    "Evaporation": 0.0,
    "Sunshine": 7.0,
    "WindGustSpeed": 25.0,
    "WindGustDir": "N",
    "WindSpeed9am": 8.0,
    "WindSpeed3pm": 12.0,
    "Humidity9am": 70.0,
    "Humidity3pm": 55.0,
    "Pressure9am": 1016.0,
    "Pressure3pm": 1014.5,
    "Cloud9am": 2.0,
    "Cloud3pm": 1.0,
    "Temp9am": 20.0,
    "Temp3pm": 28.0,
    "RainToday": "No",
    "Date_month": datetime.utcnow().month,
    "Date_day": datetime.utcnow().day,
    "Location": None
}

def _geo_lookup(city, api_key):
    params = {"q": city, "limit": 1, "appid": api_key}
    r = requests.get(OPENWEATHER_GEOCODE, params=params, timeout=6)
    r.raise_for_status()
    data = r.json()
    if not data:
        raise ValueError("no geocode result")
    return data[0]["lat"], data[0]["lon"]

def _onecall_features(lat, lon, api_key):
    params = {"lat": lat, "lon": lon, "exclude": "minutely,hourly,alerts", "appid": api_key, "units": "metric"}
    r = requests.get(OPENWEATHER_ONECALL, params=params, timeout=6)
    r.raise_for_status()
    data = r.json()
    # Simplified mapping to model features (demo-level)
    today = data.get("current", {})
    daily = data.get("daily", [{}])[0]
    features = DEMO_FEATURES.copy()
    features.update({
        "MinTemp": daily.get("temp", {}).get("min", features["MinTemp"]),
        "MaxTemp": daily.get("temp", {}).get("max", features["MaxTemp"]),
        "Temp9am": today.get("temp", features["Temp9am"]),
        "Temp3pm": daily.get("temp", {}).get("max", features["Temp3pm"]),
        "Humidity9am": today.get("humidity", features["Humidity9am"]),
        "Humidity3pm": (daily.get("humidity", features["Humidity3pm"])),
        "Pressure9am": today.get("pressure", features["Pressure9am"]),
        "Pressure3pm": today.get("pressure", features["Pressure3pm"]),
        "WindGustSpeed": today.get("wind_speed", features["WindGustSpeed"]),
        "WindSpeed9am": today.get("wind_speed", features["WindSpeed9am"]),
        "WindSpeed3pm": today.get("wind_speed", features["WindSpeed3pm"]),
        "Rainfall": daily.get("rain", features["Rainfall"]) if daily.get("rain") is not None else features["Rainfall"],
        "Location": None
    })
    return features

@bp.route("/weather", methods=["GET"])
def get_weather_features():
    """
    Returns a model-ready feature dictionary for (city,date,time).
    If OPENWEATHER_API_KEY not set or external call fails, returns DEMO_FEATURES (deterministic).
    """
    city = request.args.get("city")
    if not city:
        return jsonify({"ok": False, "error": "city required"}), 400

    key = os.environ.get("OPENWEATHER_API_KEY") or os.environ.get("OPENWEATHER_KEY") or None
    if not key:
        # return demo features
        demo = DEMO_FEATURES.copy()
        demo["Location"] = city
        return jsonify({"ok": True, "city": city, "features": demo})

    try:
        lat, lon = _geo_lookup(city, key)
        features = _onecall_features(lat, lon, key)
        features["Location"] = city
        return jsonify({"ok": True, "city": city, "features": features})
    except Exception as e:
        # On any error return demo features with error info
        demo = DEMO_FEATURES.copy()
        demo["Location"] = city
        return jsonify({"ok": False, "error": str(e), "city": city, "features": demo})
