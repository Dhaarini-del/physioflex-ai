import json
from pathlib import Path
import pandas as pd

PROJECT_DIR = Path(__file__).resolve().parent.parent

data_path = PROJECT_DIR / "data/processed/sensor_features_cleaned.csv"
features_path = PROJECT_DIR / "models/selected_features.json"
output_path = PROJECT_DIR / "sample_sensor_input.json"

# Load dataset and selected feature names
df = pd.read_csv(data_path)

with open(features_path, "r", encoding="utf-8") as f:
    feature_data = json.load(f)

if isinstance(feature_data, list):
    feature_names = feature_data
else:
    feature_names = (
        feature_data.get("selected_features")
        or feature_data.get("features")
    )

# Use a sample from Subject 5 if subject information exists
if "subject" in df.columns:
    sample_rows = df[df["subject"] == 5]
    if sample_rows.empty:
        sample_rows = df
else:
    sample_rows = df

# Select one sample
sample = sample_rows.iloc[0]

# Extract exactly the 144 model features
input_data = {
    name: float(sample[name])
    for name in feature_names
}

# Save JSON
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(input_data, f, indent=4)

print("Sample input created successfully!")
print("Number of sensor features:", len(input_data))
print("Saved at:", output_path)
print("Actual class:", sample.get("label_name", "Not available"))
