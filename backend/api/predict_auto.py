# api/predict_auto.py
from flask import Blueprint, request, jsonify, current_app
import pandas as pd
import traceback

bp = Blueprint("predict_auto", __name__, url_prefix="/api")

# try to import optional fetch helpers (these exist in your repo in api/utils/)
try:
    from .utils.fetch_weather import fetch_weather_for  # optional
except Exception:
    fetch_weather_for = None

try:
    from .utils.fetch_aqi import fetch_aqi_for  # optional (compat shim present)
except Exception:
    fetch_aqi_for = None


def build_features_from_external(city: str, date: str, time: str) -> dict:
    """
    Try to build the 23-model features using helper functions if available.
    If helpers missing or fail, returns a reasonable demo feature dict.
    """
    # demo default features (safe fallbacks)
    demo = {
        "Location": city,
        "MinTemp": 18.0,
        "MaxTemp": 30.0,
        "Temp9am": 20.0,
        "Temp3pm": 28.0,
        "Humidity9am": 70.0,
        "Humidity3pm": 55.0,
        "Pressure9am": 1016.0,
        "Pressure3pm": 1014.5,
        "Rainfall": 0.0,
        "Evaporation": 0.0,
        "Sunshine": 7.0,
        "WindGustDir": "N",
        "WindGustSpeed": 25.0,
        "WindDir9am": "N",
        "WindDir3pm": "NNW",
        "WindSpeed9am": 8.0,
        "WindSpeed3pm": 12.0,
        "Cloud9am": 2.0,
        "Cloud3pm": 1.0,
        "Temp9am": 20.0,
        "Temp3pm": 28.0,
        "RainToday": "No",
        "Date_month": int(date.split("-")[1]) if date and "-" in date else 1,
        "Date_day": int(date.split("-")[2]) if date and "-" in date else 1,
    }

    # try to fetch weather
    try:
        if fetch_weather_for:
            w = fetch_weather_for(city=city, date=date, time=time)
            if w and isinstance(w, dict) and w.get("ok"):
                # assume helper returns features under 'features' key
                f = w.get("features") or w
                # merge into demo (f overrides demo)
                demo.update({k: f[k] for k in f if k is not None})
    except Exception:
        # log but continue with demo
        pass

    # optionally incorporate AQI info if available
    try:
        if fetch_aqi_for:
            a = fetch_aqi_for(city=city)
            if a and isinstance(a, dict):
                # try to set PM2.5 etc into features if present
                measurements = a.get("measurements", [])
                for m in measurements:
                    p = m.get("parameter")
                    v = m.get("value")
                    if not p or v is None:
                        continue
                    key_map = {"pm25": "PM2.5", "pm10": "PM10", "no2": "NO2", "so2": "SO2", "o3": "O3", "co": "CO"}
                    if p.lower() in key_map:
                        demo[key_map[p.lower()]] = v
    except Exception:
        pass

    return demo


def _make_dataframe_from_features(features: dict, wrapper) -> pd.DataFrame:
    """
    Create a single-row DataFrame from features dict.
    Prefer wrapper.feature_names_ or wrapper.feature_order when available.
    """
    if not isinstance(features, dict):
        raise ValueError("features must be a dict")

    # try to discover the model's expected order
    feature_order = None
    try:
        feature_order = getattr(wrapper, "feature_names_", None) or getattr(wrapper, "feature_order", None)
    except Exception:
        feature_order = None

    if feature_order and all(isinstance(x, str) for x in feature_order):
        row = {k: features.get(k, 0) for k in feature_order}
        X = pd.DataFrame([row], columns=feature_order)
    else:
        # deterministic fallback: sort keys
        keys = sorted(features.keys())
        X = pd.DataFrame([[features[k] for k in keys]], columns=keys)
    return X


@bp.route("/predict-auto", methods=["POST"])
def predict_auto():
    """
    Request body: {"city":"Mumbai", "date":"YYYY-MM-DD", "time":"HH:MM"}
    """
    try:
        payload = request.get_json(force=True)
    except Exception as e:
        return jsonify({"ok": False, "error": "invalid JSON", "detail": str(e)}), 400

    city = payload.get("city") or payload.get("City") or payload.get("location")
    date = payload.get("date")
    time = payload.get("time")

    if not city or not date or not time:
        return jsonify({"ok": False, "error": "missing required fields: city, date, time"}), 400

    # build features (try external fetchers, else demo)
    try:
        features = build_features_from_external(city=city, date=date, time=time)
    except Exception as e:
        features = {"Location": city, "Date_month": 1, "Date_day": 1}
        # continue, we'll return error if prediction fails

    # get wrapper from app (set in app.py if available)
    wrapper = getattr(current_app, "model_wrapper", None)

    # if no wrapper, return demo prediction
    if not wrapper:
        # simple demo probability heuristic
        prob_rain = min(max((features.get("PM2.5", 0) / 200.0) * 0.5 + (features.get("Humidity9am", 50) / 200.0), 0), 1)
        p = 1 if prob_rain > 0.5 else 0
        return jsonify({
            "ok": True,
            "prediction": [int(p)],
            "probabilities": [[round(1 - prob_rain, 6), round(prob_rain, 6)]],
            "features_used": features,
            "note": "demo_prediction_no_model"
        })

    # Build DataFrame and call the wrapper safely
    try:
        X = _make_dataframe_from_features(features, wrapper)
    except Exception as e:
        return jsonify({"ok": False, "error": f"failed to build features DataFrame: {e}"}), 500

    # call prediction method(s)
    try:
        # prefer wrapper.predict_from_df
        if hasattr(wrapper, "predict_from_df"):
            pred_out = wrapper.predict_from_df(X)
        elif hasattr(wrapper, "predict"):
            # try wrapper.predict(X). If it errors, try model.predict_proba
            try:
                pred_out = wrapper.predict(X)
            except TypeError:
                # maybe wrapper.predict expects raw model input — try underlying model
                model = getattr(wrapper, "model", None)
                if model is not None and hasattr(model, "predict_proba"):
                    pred_out = model.predict_proba(X)
                else:
                    # re-raise original error
                    raise
        else:
            model = getattr(wrapper, "model", None)
            if model is not None and hasattr(model, "predict_proba"):
                pred_out = model.predict_proba(X)
            else:
                raise RuntimeError("No usable predict method found on ModelWrapper")

        # Normalize prediction output
        # Common cases:
        # - pred_out is ndarray Nx2 from predict_proba
        # - pred_out is list/ndarray of labels
        # - pred_out is dict already containing prediction/probabilities
        if isinstance(pred_out, dict):
            return jsonify({"ok": True, **pred_out})
        else:
            # try to interpret as numpy array
            try:
                import numpy as np
                arr = np.asarray(pred_out)
                if arr.ndim == 2 and arr.shape[1] >= 2:
                    probs = arr.tolist()
                    preds = [int(np.argmax(r)) for r in probs]
                    return jsonify({"ok": True, "prediction": preds, "probabilities": probs, "features_used": features})
                elif arr.ndim == 1:
                    preds = arr.tolist()
                    return jsonify({"ok": True, "prediction": preds, "features_used": features})
            except Exception:
                pass

            # fallback generic
            return jsonify({"ok": True, "prediction_raw": str(pred_out), "features_used": features})

    except Exception as e:
        tb = traceback.format_exc()
        return jsonify({"ok": False, "error": f"model predict failed: {e}", "trace": tb}), 500
