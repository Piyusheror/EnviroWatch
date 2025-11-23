# backend/api/utils/feature_mapper.py
def map_to_model_features(weather_json, aqi_json, city, date, time):
    """
    Return a dict with keys exactly matching self.feature_names in ModelWrapper.
    Fill missing with sensible defaults.
    """
    features = {}
    # Minimal mapping for demo. Expand later to fill all 23 features.
    # Example:
    features["Location"] = city or "Unknown"
    # temperature: pick current temp as both MinTemp/MaxTemp for demo
    cur = weather_json.get("current", {}) if isinstance(weather_json, dict) else {}
    temp = cur.get("temp", 0.0)
    features["MinTemp"] = float(temp)
    features["MaxTemp"] = float(temp + 4.0)
    features["Rainfall"] = float(cur.get("rain", {}).get("1h", 0.0) or 0.0)
    features["WindGustSpeed"] = float(cur.get("wind_gust", 0.0) or 0.0)
    features["WindGustDir"] = str(cur.get("wind_deg", "MISSING"))
    features["WindDir9am"] = "MISSING"
    features["WindDir3pm"] = "MISSING"
    features["WindSpeed9am"] = float(cur.get("wind_speed", 0.0) or 0.0)
    features["WindSpeed3pm"] = float(cur.get("wind_speed", 0.0) or 0.0)
    features["Humidity9am"] = float(cur.get("humidity", 0.0) or 0.0)
    features["Humidity3pm"] = float(cur.get("humidity", 0.0) or 0.0)
    features["Pressure9am"] = float(cur.get("pressure", 0.0) or 0.0)
    features["Pressure3pm"] = float(cur.get("pressure", 0.0) or 0.0)
    features["Cloud9am"] = float(cur.get("clouds", 0.0) or 0.0)
    features["Cloud3pm"] = float(cur.get("clouds", 0.0) or 0.0)
    features["Temp9am"] = float(temp)
    features["Temp3pm"] = float(temp)
    features["RainToday"] = "No" if features["Rainfall"] == 0.0 else "Yes"
    features["Date_month"] = int(date.split("-")[1]) if date and "-" in date else 0
    features["Date_day"] = int(date.split("-")[2]) if date and "-" in date else 0

    # Fill remaining features with zeros/defaults if not present
    for k in ["Evaporation","Sunshine","WindGustDir","Location"]:
        features.setdefault(k, 0.0 if k not in ["WindGustDir","Location"] else features.get(k))
    return features

