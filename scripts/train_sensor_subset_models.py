from pathlib import Path

import numpy as np
import pandas as pd

from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    f1_score,
    classification_report,
)

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"

INPUT = DATA / "sensor_features.csv"

CLASSES = [0, 1, 2]

CLASS_NAMES = [
    "Correct",
    "Too fast",
    "Low amplitude"
]

GROUP = ["subject", "exercise", "annotation_row"]

EXCLUDED = {
    "subject", "exercise", "unit",
    "annotation_row", "start", "end",
    "segment_length", "duration_seconds",
    "label", "label_name", "overlaps_previous"
}

CONFIGURATIONS = {
    "Unit 2": [2],
    "Unit 3": [3],
    "Units 2 + 3": [2, 3],
    "All five units": [1, 2, 3, 4, 5],
}

# --------------------------------------------------
# LOAD AND VALIDATE
# --------------------------------------------------

print("=" * 70)
print("PHYSIOFLEX 3.0 - SENSOR SUBSET MODEL TRAINING")
print("=" * 70)

df = pd.read_csv(INPUT)

df = df[
    ~df["overlaps_previous"].fillna(False).astype(bool)
].copy()

numeric = df.select_dtypes(include=[np.number]).columns

features = [
    col for col in numeric
    if col not in EXCLUDED
    and not col.endswith("_energy")
]

X = df[features]

if X.isna().any().any():
    raise ValueError("Missing feature values found.")

if not np.isfinite(X.to_numpy()).all():
    raise ValueError("Invalid feature values found.")

subjects = sorted(df["subject"].unique())

print("Records:", len(df))
print("Features:", len(features))
print("Subjects:", subjects)

# --------------------------------------------------
# RUN EACH SENSOR CONFIGURATION
# --------------------------------------------------

overall_results = []
subject_results = []

for config_name, selected_units in CONFIGURATIONS.items():

    print("\n" + "=" * 70)
    print("CONFIGURATION:", config_name)
    print("Selected units:", selected_units)
    print("=" * 70)

    all_repetitions = []

    for test_subject in subjects:

        train = df[
            (df["subject"] != test_subject)
            & (df["unit"].isin(selected_units))
        ].copy()

        test = df[
            (df["subject"] == test_subject)
            & (df["unit"].isin(selected_units))
        ].copy()

        if set(train["label"].unique()) != set(CLASSES):
            raise ValueError(
                f"Missing training class for subject {test_subject}"
            )

        model = RandomForestClassifier(
            n_estimators=500,
            max_features="sqrt",
            min_samples_leaf=2,
            class_weight="balanced_subsample",
            random_state=42,
            n_jobs=-1,
        )

        model.fit(train[features], train["label"])

        probabilities = model.predict_proba(test[features])

        # Ensure probability columns follow class IDs 0, 1, 2.
        probability_df = pd.DataFrame(
            0.0,
            index=test.index,
            columns=[f"p_{c}" for c in CLASSES]
        )

        for index, class_id in enumerate(model.classes_):
            probability_df[f"p_{class_id}"] = probabilities[:, index]

        test = test.join(probability_df)

        # Combine selected sensor predictions per repetition.
        grouped = test.groupby(GROUP).agg(
            true_label=("label", "first"),
            sensor_count=("unit", "nunique"),
            **{
                f"p_{c}": (f"p_{c}", "mean")
                for c in CLASSES
            }
        ).reset_index()

        # Every repetition must contain all selected sensors.
        grouped = grouped[
            grouped["sensor_count"] == len(selected_units)
        ].copy()

        if grouped.empty:
            raise ValueError(
                f"No complete repetitions for subject {test_subject}"
            )

        grouped["predicted_label"] = np.argmax(
            grouped[[f"p_{c}" for c in CLASSES]].to_numpy(),
            axis=1
        )

        all_repetitions.append(grouped)

        accuracy = accuracy_score(
            grouped["true_label"],
            grouped["predicted_label"]
        )

        print(
            f"Subject {test_subject}: "
            f"{accuracy:.2%} accuracy, "
            f"{len(grouped)} repetitions"
        )

    # --------------------------------------------------
    # OVERALL METRICS
    # --------------------------------------------------

    result = pd.concat(all_repetitions, ignore_index=True)

    y_true = result["true_label"]
    y_pred = result["predicted_label"]

    accuracy = accuracy_score(y_true, y_pred)
    balanced = balanced_accuracy_score(y_true, y_pred)

    macro_f1 = f1_score(
        y_true,
        y_pred,
        labels=CLASSES,
        average="macro"
    )

    overall_results.append({
        "configuration": config_name,
        "units": str(selected_units),
        "accuracy": accuracy,
        "balanced_accuracy": balanced,
        "macro_f1": macro_f1,
        "repetitions": len(result)
    })

    for subject in subjects:

        part = result[result["subject"] == subject]

        subject_results.append({
            "configuration": config_name,
            "subject": subject,
            "accuracy": accuracy_score(
                part["true_label"],
                part["predicted_label"]
            )
        })

    result.to_csv(
        DATA / (
            "subset_predictions_"
            + config_name.lower().replace(" ", "_").replace("+", "and")
            + ".csv"
        ),
        index=False
    )

    print("\nOverall accuracy:", round(accuracy, 4))
    print("Balanced accuracy:", round(balanced, 4))
    print("Macro F1:", round(macro_f1, 4))

    print("\nClassification report:")
    print(classification_report(
        y_true,
        y_pred,
        labels=CLASSES,
        target_names=CLASS_NAMES,
        zero_division=0
    ))

# --------------------------------------------------
# SAVE COMPARISON
# --------------------------------------------------

summary = pd.DataFrame(overall_results).sort_values(
    "macro_f1",
    ascending=False
)

per_subject = pd.DataFrame(subject_results)

summary.to_csv(
    DATA / "trained_sensor_subset_comparison.csv",
    index=False
)

per_subject.to_csv(
    DATA / "trained_sensor_subset_by_subject.csv",
    index=False
)

print("\n" + "=" * 70)
print("FINAL TRAINED SENSOR SUBSET COMPARISON")
print("=" * 70)

print(summary.to_string(index=False))

print("\nPER-SUBJECT COMPARISON")
print(per_subject.to_string(index=False))

print("\nSaved:")
print(DATA / "trained_sensor_subset_comparison.csv")
print(DATA / "trained_sensor_subset_by_subject.csv")

print("\nThese results are exploratory.")
print("Sensor configuration selection still requires independent")
print("or nested validation before final performance claims.")
