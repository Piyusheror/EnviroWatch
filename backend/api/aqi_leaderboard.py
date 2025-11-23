# api/aqi_leaderboard.py
from flask import Blueprint, jsonify
from api.utils.fetch_aqi import fetch_aqi_for

bp = Blueprint("aqi_leaderboard", __name__, url_prefix="/api")

DEFAULT_CITIES = ["Delhi","Mumbai","Kolkata","Bengaluru","Pune"]

@bp.route("/aqi-leaderboard")
def leaderboard():
    out = []
    for c in DEFAULT_CITIES:
        try:
            r = fetch_aqi_for(c)
            out.append({"city": c, "aqi": r.get("aqi_proxy", 0), "category": r.get("category")})
        except Exception:
            out.append({"city": c, "aqi": None, "category": "Unknown"})
    out = sorted(out, key=lambda x: (x["aqi"] is None, -x["aqi"] if x["aqi"] else 0))
    return jsonify({"ok": True, "leaderboard": out})
