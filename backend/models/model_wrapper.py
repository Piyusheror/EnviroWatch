import os
import joblib
import json
import pandas as pd


class ModelWrapper:
    """Lightweight wrapper that lazy-loads a CatBoost model saved either as
    joblib pickle (.pkl) or CatBoost native (.cbm). Provides `predict_from_dict`.
    """
    def __init__(self, model_dir=None):
        base = os.path.dirname(os.path.dirname(__file__))
        self.model_dir = model_dir or os.path.join(base, "models")
        # candidate files
        self.pkl_path = os.path.join(self.model_dir, "cat.pkl")
        self.cbm_path = os.path.join(self.model_dir, "cat.cbm")
        self._model = None

    def _load(self):
        # try native cbm first (safer across numpy/catboost wheel mismatches)
        if os.path.exists(self.cbm_path):
            try:
                from catboost import CatBoostClassifier
                cb = CatBoostClassifier()
                cb.load_model(self.cbm_path)
                self._model = cb
                return
            except Exception:
                pass

        if os.path.exists(self.pkl_path):
            # joblib pickle (may require same catboost binary)
            self._model = joblib.load(self.pkl_path)
            return

        raise FileNotFoundError("No model found (cat.cbm or cat.pkl) in %s" % self.model_dir)

    @property
    def model(self):
        if self._model is None:
            self._load()
        return self._model

    def predict_from_dict(self, data: dict):
        """Accepts a single-row dict with feature names -> returns prediction dict.
        Converts to a DataFrame, calls predict / predict_proba where available.
        """
        # convert to DataFrame with one row
        df = pd.DataFrame([data])

        m = self.model
        out = {"ok": True}

        # If CatBoost native API
        try:
            if hasattr(m, "predict_proba"):
                probs = m.predict_proba(df)
                # ensure serializable
                out["probabilities"] = probs.tolist()
        except Exception:
            # ignore but not fatal
            out["probabilities"] = None

        try:
            preds = m.predict(df)
            # convert numpy types
            if hasattr(preds, "tolist"):
                out["prediction"] = preds.tolist()
            else:
                out["prediction"] = preds
        except Exception:
            out["prediction"] = None

        return out