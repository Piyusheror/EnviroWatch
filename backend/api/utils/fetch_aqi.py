# api/utils/fetch_aqi.py
"""
Robust AQI fetcher for EnviroWatch.
1) Try OpenAQ v2/latest
2) If OpenAQ fails or empty -> fallback to OpenWeather Air Pollution API
"""

import os
import requests
from datetime import datetime
from typing import Dict, Any

OPENAQ_BASE = "https://api.openaq.org/v2/latest"
OW_GEO = "http://api.openweathermap.org/geo/1.0/direct"
OW_AIR = "http://api.openweathermap.org/data/2.5/air_pollution"


def _now_iso():
    return datetime.utcnow().isoformat() + "Z"


# ----------------------------------------------------
#  OPENAQ FETCH
# ----------------------------------------------------
def fetch_openaq_latest(city: str, limit: int = 1, timeout: int = 8) -> Dict[str, Any]:
    params = {"city": city, "limit": limit}
    try:
        r = requests.get(OPENAQ_BASE, params=params, timeout=timeout)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        return {"city": city, "measurements": [], "ok": False, "error": str(e), "fetched_at": _now_iso(), "raw": None}

    results = data.get("results", [])
    out = {"city": city, "measurements": [], "ok": bool(results), "fetched_at": _now_iso(), "raw": data}

    if not results:
        return out

    for loc in results[:limit]:
        loc_name = loc.get("location")
        for m in loc.get("measurements", []):
            out["measurements"].append({
                "location": loc_name,
                "parameter": m.get("parameter"),
                "value": m.get("value"),
                "unit": m.get("unit"),
                "lastUpdated": m.get("lastUpdated"),
                "sourceName": m.get("sourceName") or loc.get("sourceName")
            })

    return out


# ----------------------------------------------------
#  OPENWEATHER FALLBACK
# ----------------------------------------------------
def fetch_openweather_aqi_by_city(city: str, timeout: int = 8) -> Dict[str, Any]:
    key = os.environ.get("OPENWEATHER_API_KEY")
    if not key:
        return {"city": city, "ok": False, "error": "Missing OPENWEATHER_API_KEY",
                "measurements": [], "fetched_at": _now_iso(), "raw": None}

    try:
        # Step 1: Geocode
        geo = requests.get(OW_GEO, params={"q": city, "limit": 1, "appid": key}, timeout=timeout)
        geo.raise_for_status()
        g = geo.json()

        if not g:
            return {"city": city, "ok": False, "error": "geocode_empty",
                    "measurements": [], "fetched_at": _now_iso(), "raw": None}

        lat, lon = g[0]["lat"], g[0]["lon"]

        # Step 2: Air pollution
        ap = requests.get(OW_AIR, params={"lat": lat, "lon": lon, "appid": key}, timeout=timeout)
        ap.raise_for_status()
        raw = ap.json()

    except Exception as e:
        return {"city": city, "ok": False, "error": str(e),
                "measurements": [], "fetched_at": _now_iso(), "raw": None}

    measurements = []
    aqi_val = 0

    try:
        rows = raw.get("list", [])
        if rows:
            comp = rows[0].get("components", {})
            for k, v in comp.items():
                measurements.append({
                    "location": f"{city} (openweather)",
                    "parameter": k,
                    "value": v,
                    "unit": "µg/m3",
                    "lastUpdated": _now_iso(),
                    "sourceName": "openweather"
                })
            aqi_val = rows[0].get("main", {}).get("aqi", 0)
    except:
        pass

    return {
        "city": city,
        "measurements": measurements,
        "ok": True,
        "aqi": aqi_val,
        "fetched_at": _now_iso(),
        "raw": raw
    }


# ----------------------------------------------------
#  MAIN WRAPPER
# ----------------------------------------------------
def fetch_aqi_for(city: str, limit: int = 1, timeout: int = 8) -> Dict[str, Any]:
    """
    Try OpenAQ → if fails fallback to OpenWeather.
    Always return consistent shape.
    """

    # 1) Try OpenAQ
    oa = fetch_openaq_latest(city=city, limit=limit, timeout=timeout)
    if oa.get("ok") and oa.get("measurements"):
        return {
            "city": city,
            "aqi": 0,                 # OpenAQ doesn't return unified AQI
            "measurements": oa["measurements"],
            "ok": True,
            "fetched_at": oa["fetched_at"],
            "raw": oa["raw"]
        }

    # 2) Fallback → OpenWeather
    ow = fetch_openweather_aqi_by_city(city=city, timeout=timeout)
    if ow.get("ok") and ow.get("measurements"):
        return {
            "city": city,
            "aqi": ow.get("aqi", 0),
            "measurements": ow["measurements"],
            "ok": True,
            "fetched_at": ow["fetched_at"],
            "raw": ow["raw"]
        }

    # 3) Both failed
    return {
        "city": city,
        "aqi": 0,
        "measurements": [],
        "ok": False,
        "error": oa.get("error") or ow.get("error") or "no data",
        "fetched_at": _now_iso(),
        "raw": None
    }
