"""
PhysioFlex — Machine Learning Movement Analysis Service
Loads trained movement classification model (Extra Trees / Random Forest)
and provides inference, probability scores, and clinical feedback.
"""

import json
import warnings
from pathlib import Path
from typing import Dict, Any, List, Optional

# Suppress sklearn UserWarning regarding feature names
warnings.filterwarnings("ignore", category=UserWarning)

import joblib
import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent

# Check local or parent models directory
MODEL_DIR = BASE_DIR / "models"
if not MODEL_DIR.exists():
    MODEL_DIR = BASE_DIR.parent / "models"

DATA_DIR = BASE_DIR / "data"
if not DATA_DIR.exists():
    DATA_DIR = BASE_DIR.parent / "data"

SAMPLE_FILE = BASE_DIR / "sample_sensor_input.json"
if not SAMPLE_FILE.exists():
    SAMPLE_FILE = BASE_DIR.parent / "sample_sensor_input.json"

MODEL_PATH = MODEL_DIR / "best_movement_model.joblib"
if not MODEL_PATH.exists():
    MODEL_PATH = MODEL_DIR / "svm_model.joblib"

PIPELINE_PATH = MODEL_DIR / "feature_preprocessing_pipeline.joblib"
FEATURES_PATH = MODEL_DIR / "selected_features.json"
INFO_PATH = MODEL_DIR / "best_model_info.json"
NESTED_INFO_PATH = DATA_DIR / "reports" / "nested_loso" / "model_metadata.json"

CLINICAL_FEEDBACK = {
    "correct": {
        "title": "Correct Movement Execution",
        "description": "Movement performed within normal biomechanical velocity and full range of motion.",
        "badge_color": "green",
        "severity": "normal",
        "action": "Maintain current exercise tempo and volume."
    },
    "low_amplitude": {
        "title": "Low Movement Amplitude",
        "description": "Joint range of motion was restricted or stopped before achieving full extension/flexion.",
        "badge_color": "amber",
        "severity": "moderate",
        "action": "Gradually increase movement depth while staying within pain-free boundaries."
    },
    "too_fast": {
        "title": "Cadence Too Fast",
        "description": "Repetition was performed too rapidly, reducing eccentric muscle control.",
        "badge_color": "red",
        "severity": "high",
        "action": "Slow down repetition tempo; count 2 seconds for concentric and 3 seconds for eccentric phase."
    }
}


class MLMovementService:
    def __init__(self):
        self.model = None
        self.pipeline = None
        self.feature_names: List[str] = []
        self.metadata: Dict[str, Any] = {}
        self.validation_metadata: Dict[str, Any] = {}
        self._loaded = False
        self._load()

    def _load(self):
        try:
            if MODEL_PATH.exists() and PIPELINE_PATH.exists() and FEATURES_PATH.exists():
                self.model = joblib.load(MODEL_PATH)
                self.pipeline = joblib.load(PIPELINE_PATH)

                with FEATURES_PATH.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        self.feature_names = data
                    elif isinstance(data, dict):
                        self.feature_names = data.get("selected_features", data.get("features", []))

                if INFO_PATH.exists():
                    with INFO_PATH.open("r", encoding="utf-8") as f:
                        self.metadata = json.load(f)
                if NESTED_INFO_PATH.exists():
                    with NESTED_INFO_PATH.open("r", encoding="utf-8") as f:
                        self.validation_metadata = json.load(f)

                self._loaded = True
                print(f"[ML Service] Model loaded successfully: {self.get_model_name()} ({len(self.feature_names)} features, Accuracy: {self.get_accuracy()})")
            else:
                print(f"[ML Service] Warning: Model files not found at {MODEL_DIR}")
        except Exception as e:
            print(f"[ML Service] Error loading model: {e}")
            self._loaded = False

    def is_available(self) -> bool:
        return self._loaded and self.model is not None and self.pipeline is not None

    def get_model_name(self) -> str:
        if self.metadata and "best_model" in self.metadata:
            return self.metadata["best_model"]
        if self.model:
            return getattr(self.model, "__class__", type(self.model)).__name__
        return "Unknown"

    def get_accuracy(self) -> str:
        # Prefer subject-wise nested LOSO estimate over the legacy random-split score.
        nested = self.validation_metadata.get("nested_loso_metrics", {})
        if nested.get("accuracy") is not None:
            return f"{float(nested['accuracy']) * 100:.2f}% (nested LOSO)"
        if self.metadata and "accuracy" in self.metadata:
            return f"{float(self.metadata['accuracy']) * 100:.2f}% (legacy split; not subject-independent)"
        return "Not evaluated"

    def get_status_info(self) -> Dict[str, Any]:
        return {
            "status": "healthy" if self.is_available() else "unavailable",
            "model_name": self.get_model_name(),
            "accuracy": self.get_accuracy(),
            "macro_f1": (
                f"{float(self.validation_metadata.get('nested_loso_metrics', {}).get('macro_f1')) * 100:.2f}% (nested LOSO)"
                if self.validation_metadata.get("nested_loso_metrics", {}).get("macro_f1") is not None
                else (f"{float(self.metadata['macro_f1']) * 100:.2f}% (legacy split)" if self.metadata.get("macro_f1") is not None else "Not evaluated")
            ),
            "validation_method": "Nested Leave-One-Subject-Out" if self.validation_metadata.get("nested_loso_metrics") else "Legacy evaluation metadata",
            "limitations": self.validation_metadata.get("limitations", "Model performance has not been independently validated for clinical use."),
            "features_required": len(self.feature_names),
            "classes": self.metadata.get("classes", ["correct", "low_amplitude", "too_fast"]),
            "model_path": str(MODEL_PATH),
        }

    def get_sample_input(self) -> Dict[str, Any]:
        if SAMPLE_FILE.exists():
            try:
                with SAMPLE_FILE.open("r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {name: 0.0 for name in self.feature_names[:10]}

    def predict(self, features: Dict[str, Any]) -> Dict[str, Any]:
        if not self.is_available():
            raise RuntimeError("ML model is not loaded.")

        if not isinstance(features, dict):
            raise ValueError("Features must be a JSON object mapping feature names to numbers.")

        missing = [name for name in self.feature_names if name not in features]
        if missing:
            raise ValueError(f"Missing {len(missing)} required features: {missing[:5]}...")

        try:
            values = [float(features[name]) for name in self.feature_names]
        except (ValueError, TypeError) as exc:
            raise ValueError(f"All features must have numeric values: {exc}")

        if not np.isfinite(values).all():
            raise ValueError("All feature values must be finite numbers.")

        # Preprocess and wrap with feature names to prevent sklearn warnings
        input_df = pd.DataFrame([values], columns=self.feature_names)
        scaled_input = self.pipeline.transform(input_df)
        scaled_df = pd.DataFrame(scaled_input, columns=self.feature_names)

        prediction_raw = self.model.predict(scaled_df)[0]
        predicted_class = str(prediction_raw)

        # Class probabilities if available
        probabilities = {}
        if hasattr(self.model, "predict_proba"):
            try:
                probs = self.model.predict_proba(scaled_df)[0]
                model_classes = getattr(self.model, "classes_", [])
                for cls, prob in zip(model_classes, probs):
                    probabilities[str(cls)] = round(float(prob), 4)
            except Exception:
                pass

        feedback = CLINICAL_FEEDBACK.get(predicted_class, {
            "title": predicted_class.replace("_", " ").title(),
            "description": f"Classified as {predicted_class}.",
            "badge_color": "blue",
            "severity": "info",
            "action": "Consult your physiotherapist."
        })

        return {
            "status": "success",
            "predicted_class": predicted_class,
            "predicted_label": predicted_class.replace("_", " ").title(),
            "model_name": self.get_model_name(),
            "model_accuracy": self.get_accuracy(),
            "probabilities": probabilities,
            "feedback": feedback
        }


# Singleton service instance
ml_service = MLMovementService()
