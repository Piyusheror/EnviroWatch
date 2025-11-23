# api/aqi.py
from flask import Blueprint, request, jsonify
from api.utils.fetch_aqi import fetch_aqi_for

bp = Blueprint("aqi", __name__, url_prefix="/api")

@bp.route("/aqi", methods=["GET"])
def get_aqi():
    """
    Returns normalized AQI summary for a city.
    Uses fetch_aqi_for => will return demo fallback if OpenAQ fails.
    Query params: city (required)
    """
    city = request.args.get("city")
    if not city:
        return jsonify({"ok": False, "error": "city required"}), 400

    try:
        res = fetch_aqi_for(city)
    except Exception as e:
        return jsonify({"ok": False, "error": f"internal error: {e}"}), 500

    # If fetch_aqi_for returns the wrapped summary, return it directly.
    # It always returns {"aqi": {...}, "city": city, "ok": True} even for demo.
    return jsonify(res), 200
