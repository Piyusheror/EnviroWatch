from flask import Blueprint, request, jsonify
# replace the bad import with:
from flask import current_app

# then, whenever the endpoint needs the wrapper, use:
wrapper = None
# (this is identical to how your predict_auto uses current_app)


predict_bp = Blueprint("predict", __name__)


def get_wrapper():
    """Return the ModelWrapper attached to the Flask app, read lazily at request time."""
    try:
        from flask import current_app
        return getattr(current_app, "model_wrapper", None)
    except RuntimeError:
        # no app context available
        return None


@predict_bp.route("/predict", methods=["POST"])
def predict():
    try:
        payload = request.json

        if not payload:
            return jsonify({"error": "No JSON received"}), 400

        wrapper = get_wrapper()
        if not wrapper:
            return jsonify({'ok': False, 'error': 'no_model_loaded', 'note': 'prediction requires a loaded ModelWrapper on app'}) , 500
        # wrapper should expose a predict / predict_from_dict / predict_from_df API
        # try common names in order
        try:
            if hasattr(wrapper, 'predict_from_dict'):
                result = wrapper.predict_from_dict(payload)
            elif hasattr(wrapper, 'predict'):
                # some wrappers accept dicts directly
                result = wrapper.predict(payload)
            elif hasattr(wrapper, 'predict_from_df'):
                # convert single-row DF if needed
                import pandas as pd
                X = pd.DataFrame([payload])
                result = wrapper.predict_from_df(X)
            else:
                # last-resort: try wrapper.model.predict_proba if available
                model = getattr(wrapper, 'model', None)
                if model and hasattr(model, 'predict_proba'):
                    import pandas as pd
                    X = pd.DataFrame([payload])
                    probs = model.predict_proba(X)
                    import numpy as np
                    preds = [int(np.argmax(r)) for r in probs]
                    result = {'prediction': preds, 'probabilities': probs.tolist()}
                else:
                    raise RuntimeError('no_predict_method_on_wrapper')
        except Exception as e:
            return jsonify({'ok': False, 'error': 'model_predict_failed', 'detail': str(e)}), 500

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500
