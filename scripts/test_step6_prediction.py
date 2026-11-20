
import json
import urllib.request
import urllib.error
from pathlib import Path

import pandas as pd

PROJECT_DIR = Path(__file__).resolve().parent.parent

DATA_PATH = (
    PROJECT_DIR / "data" / "processed" /
    "sensor_features_cleaned.csv"
)

FEATURES_PATH = (
    PROJECT_DIR / "models" / "selected_features.json"
)

# Load selected feature names
with open(FEATURES_PATH, "r") as file:
    feature_data = json.load(file)

if isinstance(feature_data, list):
    feature_names = feature_data
else:
    feature_names = feature_data.get(
        "selected_features",
        feature_data.get("features")
    )

if not feature_names:
    raise ValueError("Could not load selected feature names.")

# Load dataset
df = pd.read_csv(DATA_PATH)

# Select one real sample from unseen Subject 5
sample = df[df["subject"] == 5].iloc[0]

# Build raw sensor input
sensor_features = {
    name: float(sample[name])
    for name in feature_names
}

payload = {
    "features": sensor_features
}

# Send POST request
url = "http://127.0.0.1:5000/predict"

request = urllib.request.Request(
    url,
    data=json.dumps(payload).encode("utf-8"),
    headers={"Content-Type": "application/json"},
    method="POST"
)

try:
    with urllib.request.urlopen(request) as response:
        result = json.loads(response.read().decode("utf-8"))

    print("\nPHYSIOFLEX 3.0 PREDICTION")
    print("=" * 40)
    print("Actual class:", sample["label_name"])
    print("Predicted class:", result.get("predicted_class"))
    print("API status:", result.get("status"))

except urllib.error.HTTPError as error:
    print("HTTP Error:", error.code)
    print(error.read().decode("utf-8"))

except Exception as error:
    print("Error:", error)
