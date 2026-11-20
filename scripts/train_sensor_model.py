from pathlib import Path

import pandas as pd
import numpy as np

from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)

# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

ROOT = Path(__file__).resolve().parents[1]

INPUT_FILE = ROOT / "data" / "processed" / "sensor_features.csv"
OUTPUT_DIR = ROOT / "data" / "processed"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

CLASS_NAMES = {
    0: "Correct",
    1: "Too fast",
    2: "Low amplitude",
}

CLASS_IDS = [0, 1, 2]

# Metadata must never be used as model features.
EXCLUDED_COLUMNS = {
    "subject",
    "exercise",
    "unit",
    "annotation_row",
    "start",
    "end",
    "segment_length",
    "duration_seconds",
    "label",
    "label_name",
    "overlaps_previous",
}

# --------------------------------------------------
# LOAD DATA
# --------------------------------------------------

print("=" * 65)
print("PHYSIOFLEX 3.0 - SENSOR MOVEMENT CLASSIFICATION")
print("=" * 65)

if not INPUT_FILE.exists():
    raise FileNotFoundError(f"Feature file not found: {INPUT_FILE}")

df = pd.read_csv(INPUT_FILE)

print("\nOriginal dataset shape:", df.shape)

required_columns = {
    "subject", "exercise", "unit",
    "annotation_row", "label", "overlaps_previous"
}

missing = required_columns - set(df.columns)

if missing:
    raise ValueError(f"Missing required columns: {missing}")

# Remove records affected by known annotation overlaps.
overlap_count = int(df["overlaps_previous"].fillna(False).astype(bool).sum())

df = df[
    ~df["overlaps_previous"].fillna(False).astype(bool)
].copy()

print("Overlap-affected sensor records excluded:", overlap_count)
print("Records remaining:", len(df))

# --------------------------------------------------
# SELECT FEATURES
# --------------------------------------------------

numeric_columns = df.select_dtypes(include=[np.number]).columns.tolist()

feature_columns = [
    col for col in numeric_columns
    if col not in EXCLUDED_COLUMNS
    and not col.endswith("_energy")
]

if not feature_columns:
    raise ValueError("No usable numerical features found.")

X = df[feature_columns].copy()
y = df["label"].astype(int)

if set(y.unique()) != set(CLASS_IDS):
    raise ValueError(f"Unexpected class labels: {sorted(y.unique())}")

if X.isna().any().any():
    raise ValueError("Missing values found in feature data.")

if not np.isfinite(X.to_numpy()).all():
    raise ValueError("Infinite or invalid numerical values found.")

print("\nNumber of sensor features:", len(feature_columns))
print("Classes:", CLASS_NAMES)

print("\nClass distribution:")
for class_id in CLASS_IDS:
    print(
        f"{class_id} - {CLASS_NAMES[class_id]}:",
        int((y == class_id).sum())
    )

print("\nSubjects:", sorted(df["subject"].unique()))

# --------------------------------------------------
# LEAVE-ONE-SUBJECT-OUT VALIDATION
# --------------------------------------------------

all_predictions = []
all_probabilities = []

subjects = sorted(df["subject"].unique())

if len(subjects) < 3:
    raise ValueError("Not enough subjects for subject-independent testing.")

for test_subject in subjects:

    print("\n" + "-" * 55)
    print(f"TESTING ON SUBJECT {test_subject}")
    print("-" * 55)

    train_mask = df["subject"] != test_subject
    test_mask = df["subject"] == test_subject

    X_train = X.loc[train_mask]
    y_train = y.loc[train_mask]

    X_test = X.loc[test_mask]
    y_test = y.loc[test_mask]

    # Every fold must contain all three training classes.
    if set(y_train.unique()) != set(CLASS_IDS):
        raise ValueError(
            f"Training fold for subject {test_subject} "
            "does not contain all three classes."
        )

    model = RandomForestClassifier(
        n_estimators=500,
        max_features="sqrt",
        min_samples_leaf=2,
        class_weight="balanced_subsample",
        random_state=42,
        n_jobs=-1,
    )

    model.fit(X_train, y_train)

    predictions = model.predict(X_test)
    probabilities = model.predict_proba(X_test)

    # Save out-of-subject predictions.
    fold_result = df.loc[test_mask, [
        "subject", "exercise", "unit",
        "annotation_row", "label"
    ]].copy()

    fold_result["predicted_label"] = predictions

    for class_index, class_id in enumerate(model.classes_):
        fold_result[f"probability_{class_id}"] = probabilities[
            :, class_index
        ]

    all_predictions.append(fold_result)

    print("Training records:", len(X_train))
    print("Testing records:", len(X_test))
    print(
        "Sensor-record accuracy:",
        round(accuracy_score(y_test, predictions), 4)
    )
    print(
        "Sensor-record macro F1:",
        round(f1_score(y_test, predictions, average="macro"), 4)
    )

# --------------------------------------------------
# COMBINE ALL HELD-OUT PREDICTIONS
# --------------------------------------------------

results = pd.concat(all_predictions, ignore_index=True)

prediction_file = OUTPUT_DIR / "sensor_loso_predictions.csv"
results.to_csv(prediction_file, index=False)

print("\n" + "=" * 65)
print("SENSOR-RECORD LEVEL RESULTS")
print("=" * 65)

print("\nAccuracy:",
      round(accuracy_score(
          results["label"], results["predicted_label"]
      ), 4))

print("Balanced accuracy:",
      round(balanced_accuracy_score(
          results["label"], results["predicted_label"]
      ), 4))

print("Macro F1:",
      round(f1_score(
          results["label"],
          results["predicted_label"],
          average="macro"
      ), 4))

print("\nClassification report:")
print(classification_report(
    results["label"],
    results["predicted_label"],
    labels=CLASS_IDS,
    target_names=[CLASS_NAMES[i] for i in CLASS_IDS],
    zero_division=0
))

print("Confusion matrix:")
print(confusion_matrix(
    results["label"],
    results["predicted_label"],
    labels=CLASS_IDS
))

# --------------------------------------------------
# REPETITION-LEVEL PROBABILITY AGGREGATION
# --------------------------------------------------

probability_columns = [
    f"probability_{class_id}" for class_id in CLASS_IDS
]

group_columns = ["subject", "exercise", "annotation_row"]

# A repetition should have exactly five sensor-unit records.
unit_counts = results.groupby(group_columns)["unit"].nunique()

valid_groups = unit_counts[unit_counts == 5].index

complete = results.set_index(group_columns).loc[
    results.set_index(group_columns).index.isin(valid_groups)
].reset_index()

incomplete_count = len(unit_counts) - len(valid_groups)

print("\nIncomplete five-unit repetitions excluded:", incomplete_count)

if complete.empty:
    raise ValueError("No complete five-unit repetitions available.")

# Average class probabilities across the five sensor units.
aggregated = complete.groupby(group_columns).agg(
    true_label=("label", "first"),
    **{
        col: (col, "mean")
        for col in probability_columns
    }
).reset_index()

aggregated["predicted_label"] = np.argmax(
    aggregated[probability_columns].to_numpy(),
    axis=1
)

repetition_file = OUTPUT_DIR / "repetition_loso_predictions.csv"
aggregated.to_csv(repetition_file, index=False)

print("\n" + "=" * 65)
print("REPETITION-LEVEL RESULTS")
print("=" * 65)

print("Complete repetitions:", len(aggregated))

print("\nAccuracy:",
      round(accuracy_score(
          aggregated["true_label"],
          aggregated["predicted_label"]
      ), 4))

print("Balanced accuracy:",
      round(balanced_accuracy_score(
          aggregated["true_label"],
          aggregated["predicted_label"]
      ), 4))

print("Macro F1:",
      round(f1_score(
          aggregated["true_label"],
          aggregated["predicted_label"],
          average="macro"
      ), 4))

print("\nClassification report:")
print(classification_report(
    aggregated["true_label"],
    aggregated["predicted_label"],
    labels=CLASS_IDS,
    target_names=[CLASS_NAMES[i] for i in CLASS_IDS],
    zero_division=0
))

print("Confusion matrix:")
print(confusion_matrix(
    aggregated["true_label"],
    aggregated["predicted_label"],
    labels=CLASS_IDS
))

# --------------------------------------------------
# PER-SUBJECT REPETITION RESULTS
# --------------------------------------------------

print("\n" + "=" * 65)
print("PER-SUBJECT REPETITION PERFORMANCE")
print("=" * 65)

for subject in subjects:

    subject_data = aggregated[
        aggregated["subject"] == subject
    ]

    if subject_data.empty:
        continue

    print(
        f"Subject {subject}: "
        f"Accuracy = "
        f"{accuracy_score(subject_data['true_label'], subject_data['predicted_label']):.4f}, "
        f"Macro F1 = "
        f"{f1_score(subject_data['true_label'], subject_data['predicted_label'], average='macro'):.4f}, "
        f"Repetitions = {len(subject_data)}"
    )

print("\n" + "=" * 65)
print("TRAINING AND EVALUATION COMPLETED")
print("=" * 65)

print("\nGenerated files:")
print(prediction_file)
print(repetition_file)

print("\nImportant:")
print("These are experimental results from five subjects.")
print("They do not establish clinical accuracy or generalization.")
