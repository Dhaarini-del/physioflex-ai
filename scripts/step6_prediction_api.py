import json
import warnings
from pathlib import Path

# Silence scikit-learn feature name validation warnings
warnings.filterwarnings("ignore", category=UserWarning)

import joblib
import numpy as np
import pandas as pd
from flask import Flask, jsonify, render_template, request

# --------------------------------------------------
# PROJECT PATHS
# --------------------------------------------------
PROJECT_DIR = Path(__file__).resolve().parent.parent
MODEL_DIR = PROJECT_DIR / "models"

MODEL_PATH = MODEL_DIR / "best_movement_model.joblib"
if not MODEL_PATH.is_file():
    MODEL_PATH = MODEL_DIR / "svm_model.joblib"
PIPELINE_PATH = MODEL_DIR / "feature_preprocessing_pipeline.joblib"
FEATURES_PATH = MODEL_DIR / "selected_features.json"
INFO_PATH = MODEL_DIR / "best_model_info.json"

TEMPLATE_DIR = PROJECT_DIR / "templates"
STATIC_DIR = PROJECT_DIR / "static"

# --------------------------------------------------
# CHECK FILES
# --------------------------------------------------
for path in (MODEL_PATH, PIPELINE_PATH, FEATURES_PATH):
    if not path.is_file():
        raise FileNotFoundError(f"Missing file: {path}")

if not (TEMPLATE_DIR / "index.html").is_file():
    raise FileNotFoundError(
        f"index.html not found in: {TEMPLATE_DIR}"
    )

if not STATIC_DIR.is_dir():
    raise FileNotFoundError(f"Static folder not found: {STATIC_DIR}")

# --------------------------------------------------
# LOAD MODEL & METADATA
# --------------------------------------------------
print("Loading PhysioFlex 3.0 model and preprocessing pipeline...")

model = joblib.load(MODEL_PATH)
preprocessing_pipeline = joblib.load(PIPELINE_PATH)

with FEATURES_PATH.open("r", encoding="utf-8") as file:
    feature_data = json.load(file)

if isinstance(feature_data, list):
    feature_names = feature_data
elif isinstance(feature_data, dict):
    feature_names = (
        feature_data.get("selected_features")
        or feature_data.get("features")
    )
else:
    raise ValueError("Invalid selected_features.json format")

if not isinstance(feature_names, list) or not feature_names:
    raise ValueError("No selected feature names found")

if len(feature_names) != len(set(feature_names)):
    raise ValueError("Duplicate feature names found")

# Read best model metadata if present
model_display_name = getattr(model, "__class__", type(model)).__name__
model_accuracy_str = "96.67%"

if INFO_PATH.is_file():
    try:
        with INFO_PATH.open("r", encoding="utf-8") as file:
            info = json.load(file)
        model_display_name = info.get("best_model", model_display_name)
        if "accuracy" in info:
            model_accuracy_str = f"{float(info['accuracy']) * 100:.2f}%"
    except Exception:
        pass

print("Model loaded successfully.")
print(f"Selected model: {model_display_name} (Accuracy: {model_accuracy_str})")
print(f"Selected sensor features: {len(feature_names)}")

# --------------------------------------------------
# FLASK APP
# --------------------------------------------------
app = Flask(
    __name__,
    template_folder=str(TEMPLATE_DIR),
    static_folder=str(STATIC_DIR),
    static_url_path="/static"
)


@app.route("/", methods=["GET"])
def home():
    return render_template(
        "index.html",
        model_name=model_display_name,
        accuracy=model_accuracy_str,
        required_features=len(feature_names)
    )


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "healthy",
        "model": model_display_name,
        "accuracy": model_accuracy_str,
        "features_required": len(feature_names)
    })


@app.route("/predict", methods=["POST"])
def predict():
    try:
        data = request.get_json(silent=True)

        if not isinstance(data, dict):
            return jsonify({
                "status": "error",
                "message": "Please send valid JSON data."
            }), 400

        # Accept either {"features": {...}} or a direct feature dictionary
        features = data.get("features", data)

        if not isinstance(features, dict):
            return jsonify({
                "status": "error",
                "message": "Features must be a JSON object."
            }), 400

        missing = [
            name for name in feature_names
            if name not in features
        ]

        if missing:
            return jsonify({
                "status": "error",
                "message": f"Missing {len(missing)} features.",
                "missing_features": missing
            }), 400

        try:
            values = [float(features[name]) for name in feature_names]
        except (TypeError, ValueError):
            return jsonify({
                "status": "error",
                "message": "All feature values must be numeric."
            }), 400

        if not np.isfinite(values).all():
            return jsonify({
                "status": "error",
                "message": "Feature values must be finite numbers."
            }), 400

        input_df = pd.DataFrame(
            [values],
            columns=feature_names
        )

        scaled_input = preprocessing_pipeline.transform(input_df)
        scaled_df = pd.DataFrame(scaled_input, columns=feature_names)
        prediction = model.predict(scaled_df)

        predicted_class = str(prediction[0])

        return jsonify({
            "status": "success",
            "predicted_class": predicted_class,
            "message": "Movement prediction completed successfully."
        })

    except Exception as error:
        app.logger.exception("Prediction error")
        return jsonify({
            "status": "error",
            "message": str(error)
        }), 500


# --------------------------------------------------
# START SERVER
# --------------------------------------------------
if __name__ == "__main__":
    print("\nStarting PhysioFlex 3.0 web server...")
    print("Open http://127.0.0.1:5000/ in your browser")

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False
    )
