# backend/api/visualize.py
from flask import Blueprint, request, jsonify
from .utils.fetch_weather import geocode_city, fetch_weather_for
from .utils.fetch_aqi import fetch_openaq_latest
from datetime import datetime, timedelta

bp = Blueprint("visualize", __name__, url_prefix="/api")

@bp.route("/visualize", methods=["GET"])
def visualize():
    city = request.args.get("city")
    if not city:
        return jsonify({"ok": False, "error": "city required"}), 400
    lat, lon = geocode_city(city)
    if lat is None:
        return jsonify({"ok": False, "error": "geocode failed"}), 400

    # quick demo: call current daily hourly and return last 7 hourly temps + pm25
    w = fetch_weather_for(None, lat, lon)
    a = fetch_openaq_latest(city)
    # build trivial timeseries of length 7 for demo:
    now = datetime.utcnow()
    temps = []
    pm25s = []
    for i in range(7):
        t = (now - timedelta(days=i)).strftime("%Y-%m-%d")
        temps.append({"date": t, "temp": w.get("current", {}).get("temp", None)})
        pm25s.append({"date": t, "pm25": a.get("pm25")})
    return jsonify({"ok": True, "temps": list(reversed(temps)), "pm25": list(reversed(pm25s))})

