# api/utils/fetch_weather.py
import os, requests, datetime

OPENWEATHER_KEY = os.environ.get("OPENWEATHER_API_KEY")

def geocode_city(city):
    if not OPENWEATHER_KEY:
        raise RuntimeError("OPENWEATHER_API_KEY not set")
    url = "http://api.openweathermap.org/geo/1.0/direct"
    params = {"q": city, "limit": 1, "appid": OPENWEATHER_KEY}
    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    data = r.json()
    if not data:
        raise ValueError(f"City not found: {city}")
    return data[0]["lat"], data[0]["lon"]

def fetch_weather_for(city, date=None, time=None):
    """
    Return a dict of approximate features needed by the model for the given city/date/time.
    If date/time is today, use current/hourly. For simplicity we pull current + hourly and map to 9am/3pm if requested.
    """
    lat, lon = geocode_city(city)
    url = "https://api.openweathermap.org/data/2.5/onecall"
    params = {"lat": lat, "lon": lon, "exclude": "minutely,alerts", "appid": OPENWEATHER_KEY, "units":"metric"}
    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    j = r.json()

    # Build simple mapping for required features; we pick 'current' + nearest hourly for 9am/3pm
    now = datetime.datetime.utcnow()
    # helper: find closest hour forecast timestamp for 9:00 and 15:00 local (approx)
    def pick_hourly(target_hour_local):
        hourly = j.get("hourly", [])
        if not hourly:
            return None
        # approximate: compare UTC hour to target (not perfect across timezone but acceptable for demo)
        target_ts = None
        for h in hourly[:48]:
            dt = datetime.datetime.utcfromtimestamp(h["dt"])
            if dt.hour == target_hour_local:
                return h
        return hourly[0]

    # For model: pick reasonable values
    curr = j.get("current", {})
    hour9 = pick_hourly(9)
    hour15 = pick_hourly(15)

    out = {
        "MinTemp": curr.get("temp"),
        "MaxTemp": curr.get("temp"),
        "Temp9am": hour9.get("temp") if hour9 else curr.get("temp"),
        "Temp3pm": hour15.get("temp") if hour15 else curr.get("temp"),
        "Humidity9am": hour9.get("humidity") if hour9 else curr.get("humidity"),
        "Humidity3pm": hour15.get("humidity") if hour15 else curr.get("humidity"),
        "Pressure9am": hour9.get("pressure") if hour9 else curr.get("pressure"),
        "Pressure3pm": hour15.get("pressure") if hour15 else curr.get("pressure"),
        "Rainfall": (curr.get("rain", {}).get("1h", 0) if curr else 0),
        "WindGustSpeed": curr.get("wind_gust", 0) if curr else 0,
        "WindGustDir": None,
        "WindDir9am": None,
        "WindDir3pm": None,
        "WindSpeed9am": hour9.get("wind_speed", 0) if hour9 else curr.get("wind_speed",0),
        "WindSpeed3pm": hour15.get("wind_speed", 0) if hour15 else curr.get("wind_speed",0),
        "Cloud9am": hour9.get("clouds", 0) if hour9 else curr.get("clouds", 0),
        "Cloud3pm": hour15.get("clouds", 0) if hour15 else curr.get("clouds", 0),
        "Evaporation": 0.0,
        "Sunshine": 0.0,
        "Date_month": date.month if date else now.month,
        "Date_day": date.day if date else now.day,
        "Location": city,
        "RainToday": "No"
    }

    # Try to get wind direction strings (convert degrees -> cardinal)
    def deg_to_cardinal(d):
        if d is None:
            return "MISSING"
        dirs = ["N","NNE","NE","ENE","E","ESE","SE","SSE","S","SSW","SW","WSW","W","WNW","NW","NNW"]
        ix = int((d / 22.5) + 0.5) % 16
        return dirs[ix]
    if curr.get("wind_deg") is not None:
        out["WindGustDir"] = deg_to_cardinal(curr.get("wind_deg"))
    if hour9 and hour9.get("wind_deg") is not None:
        out["WindDir9am"] = deg_to_cardinal(hour9.get("wind_deg"))
    if hour15 and hour15.get("wind_deg") is not None:
        out["WindDir3pm"] = deg_to_cardinal(hour15.get("wind_deg"))

    return out
