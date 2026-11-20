
import json
import urllib.request
import urllib.error
from pathlib import Path

import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    classification_report,
    confusion_matrix
)

# ==================================================
# PHYSIOFLEX 3.0 - STEP 7
# FINAL SYSTEM TESTING
# ==================================================

PROJECT_DIR = Path(__file__).resolve().parent.parent

DATA_PATH = (
    PROJECT_DIR / "data" / "processed" /
    "sensor_features_cleaned.csv"
)

FEATURES_PATH = (
    PROJECT_DIR / "models" / "selected_features.json"
)

REPORT_DIR = (
    PROJECT_DIR / "data" / "processed" / "reports"
)

REPORT_DIR.mkdir(parents=True, exist_ok=True)

API_URL = "http://127.0.0.1:5000/predict"
HEALTH_URL = "http://127.0.0.1:5000/health"

print("=" * 60)
print("PHYSIOFLEX 3.0 - STEP 7")
print("FINAL SYSTEM TESTING")
print("=" * 60)

# --------------------------------------------------
# 1. LOAD FEATURE NAMES
# --------------------------------------------------

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
    raise ValueError("Feature names could not be loaded.")

print("\nTotal required features:", len(feature_names))

# --------------------------------------------------
# 2. CHECK API HEALTH
# --------------------------------------------------

print("\n1. CHECKING API HEALTH")

try:
    with urllib.request.urlopen(HEALTH_URL, timeout=10) as response:
        health_data = json.loads(
            response.read().decode("utf-8")
        )

    if health_data.get("status") != "healthy":
        raise RuntimeError("API health check failed.")

    print("API health check: PASSED")
    print("Model:", health_data.get("model"))
    print("Required features:", health_data.get("features_required"))

except Exception as error:
    raise SystemExit(
        f"API is unavailable. Start step6_prediction_api.py first.\n{error}"
    )

# --------------------------------------------------
# 3. LOAD TEST DATA
# --------------------------------------------------

print("\n2. LOADING TEST DATA")

test_raw_path = PROJECT_DIR / "data" / "processed" / "test_raw_samples.csv"
if test_raw_path.exists():
    test_df = pd.read_csv(test_raw_path).reset_index(drop=True)
else:
    df = pd.read_csv(DATA_PATH)
    if "subject" not in df.columns or "label_name" not in df.columns:
        raise ValueError("Dataset is missing subject or label_name.")
    test_df = df[df["subject"] == 5].copy().reset_index(drop=True)

if test_df.empty:
    raise ValueError("No test records found.")

missing_columns = [
    name for name in feature_names
    if name not in test_df.columns
]

if missing_columns:
    raise ValueError(
        f"Missing sensor columns: {missing_columns}"
    )

print("Test records:", len(test_df))
if "subject" in test_df.columns:
    print("Test subjects:", sorted(test_df["subject"].unique().tolist()))

# --------------------------------------------------
# 4. TEST ALL RECORDS THROUGH THE API
# --------------------------------------------------

print("\n3. TESTING MOVEMENT PREDICTIONS")
print("Please wait...")

actual_labels = []
predicted_labels = []
failed_records = []

for index, row in test_df.iterrows():

    sensor_features = {}

    for name in feature_names:
        value = pd.to_numeric(row[name], errors="coerce")

        if pd.isna(value):
            sensor_features[name] = None
        else:
            sensor_features[name] = float(value)

    payload = {"features": sensor_features}

    request = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            result = json.loads(
                response.read().decode("utf-8")
            )

        if result.get("status") != "success":
            raise ValueError(result)

        actual_labels.append(str(row["label_name"]))
        predicted_labels.append(str(result["predicted_class"]))

    except Exception as error:
        failed_records.append({
            "record": index,
            "error": str(error)
        })

    if (index + 1) % 100 == 0:
        print(f"Processed {index + 1}/{len(test_df)} records")

# --------------------------------------------------
# 5. CALCULATE MODEL PERFORMANCE
# --------------------------------------------------

print("\n4. FINAL PERFORMANCE RESULTS")

successful = len(actual_labels)

if successful == 0:
    raise SystemExit("No records were successfully predicted.")

accuracy = accuracy_score(actual_labels, predicted_labels)

precision = precision_score(
    actual_labels,
    predicted_labels,
    average="macro",
    zero_division=0
)

recall = recall_score(
    actual_labels,
    predicted_labels,
    average="macro",
    zero_division=0
)

f1 = f1_score(
    actual_labels,
    predicted_labels,
    average="macro",
    zero_division=0
)

print("\nSuccessful predictions:", successful)
print("Failed predictions:", len(failed_records))
print(f"Accuracy:  {accuracy:.4f}")
print(f"Precision: {precision:.4f}")
print(f"Recall:    {recall:.4f}")
print(f"Macro F1:  {f1:.4f}")

# --------------------------------------------------
# 6. CLASSIFICATION REPORT
# --------------------------------------------------

classes = sorted(set(actual_labels) | set(predicted_labels))

report = classification_report(
    actual_labels,
    predicted_labels,
    labels=classes,
    output_dict=True,
    zero_division=0
)

print("\nCLASSIFICATION REPORT")
print(
    classification_report(
        actual_labels,
        predicted_labels,
        labels=classes,
        zero_division=0
    )
)

# --------------------------------------------------
# 7. CONFUSION MATRIX
# --------------------------------------------------

matrix = confusion_matrix(
    actual_labels,
    predicted_labels,
    labels=classes
)

matrix_df = pd.DataFrame(
    matrix,
    index=classes,
    columns=classes
)

matrix_path = REPORT_DIR / "step7_final_confusion_matrix.csv"
matrix_df.to_csv(matrix_path)

# --------------------------------------------------
# 8. SAVE PREDICTIONS
# --------------------------------------------------

results_df = pd.DataFrame({
    "actual_class": actual_labels,
    "predicted_class": predicted_labels
})

results_path = REPORT_DIR / "step7_final_predictions.csv"
results_df.to_csv(results_path, index=False)

# --------------------------------------------------
# 9. TEST INVALID INPUT
# --------------------------------------------------

print("\n5. TESTING INVALID INPUT HANDLING")

invalid_payload = {
    "features": {}
}

invalid_request = urllib.request.Request(
    API_URL,
    data=json.dumps(invalid_payload).encode("utf-8"),
    headers={"Content-Type": "application/json"},
    method="POST"
)

try:
    with urllib.request.urlopen(invalid_request) as response:
        invalid_status = response.status

except urllib.error.HTTPError as error:
    invalid_status = error.code

invalid_test_passed = invalid_status == 400

print(
    "Invalid input test:",
    "PASSED" if invalid_test_passed else "FAILED"
)
print("HTTP status:", invalid_status)

# --------------------------------------------------
# 10. SAVE FINAL REPORT
# --------------------------------------------------

summary = {
    "project": "PhysioFlex 3.0",
    "tested_subject": "stratified_test_holdout",
    "total_test_records": len(test_df),
    "successful_predictions": successful,
    "failed_predictions": len(failed_records),
    "accuracy": accuracy,
    "macro_precision": precision,
    "macro_recall": recall,
    "macro_f1_score": f1,
    "invalid_input_test": (
        "PASSED" if invalid_test_passed else "FAILED"
    ),
    "classification_report": report,
    "failed_record_details": failed_records
}

summary_path = REPORT_DIR / "step7_final_testing_report.json"

with open(summary_path, "w") as file:
    json.dump(summary, file, indent=4)

# --------------------------------------------------
# 11. FINAL STATUS
# --------------------------------------------------

print("\n" + "=" * 60)
print("STEP 7 FINAL TESTING SUMMARY")
print("=" * 60)

all_predictions_passed = (
    successful == len(test_df) and len(failed_records) == 0
)

print(
    "API prediction test:",
    "PASSED" if all_predictions_passed else "PARTIAL / FAILED"
)

print(
    "Invalid input test:",
    "PASSED" if invalid_test_passed else "FAILED"
)

print("\nGenerated files:")
print("- step7_final_testing_report.json")
print("- step7_final_predictions.csv")
print("- step7_final_confusion_matrix.csv")

print("\nReport folder:", REPORT_DIR)

print("\nSTEP 7 TESTING FINISHED")
print("=" * 60)
