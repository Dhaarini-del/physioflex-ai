
from pathlib import Path
import pandas as pd
import numpy as np

from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    f1_score,
    classification_report
)

ROOT = Path(__file__).resolve().parents[1]

FILE = (
    ROOT / "data" / "processed"
    / "sensor_loso_predictions.csv"
)

df = pd.read_csv(FILE)

CLASSES = [0, 1, 2]

PROB_COLS = [
    f"probability_{i}" for i in CLASSES
]

GROUP = [
    "subject",
    "exercise",
    "annotation_row"
]

# --------------------------------------------------
# CHECK DATA
# --------------------------------------------------

print("=" * 65)
print("PHYSIOFLEX 3.0 - SENSOR FUSION COMPARISON")
print("=" * 65)

required = GROUP + [
    "unit", "label", "predicted_label"
] + PROB_COLS

missing = set(required) - set(df.columns)

if missing:
    raise ValueError(f"Missing columns: {missing}")

if df.duplicated(GROUP + ["unit"]).any():
    raise ValueError("Duplicate sensor-unit records found.")

unit_counts = df.groupby(GROUP)["unit"].nunique()

if not (unit_counts == 5).all():
    raise ValueError("Some repetitions do not have five sensor units.")

# --------------------------------------------------
# PREPARE EXPERIMENTS
# --------------------------------------------------

experiments = {
    "Unit 1": [1],
    "Unit 2": [2],
    "Unit 3": [3],
    "Unit 4": [4],
    "Unit 5": [5],
    "Units 2 + 3": [2, 3],
    "All five units": [1, 2, 3, 4, 5]
}

summary = []

# --------------------------------------------------
# EVALUATE SENSOR SELECTION AND FUSION
# --------------------------------------------------

for name, selected_units in experiments.items():

    subset = df[df["unit"].isin(selected_units)].copy()

    aggregated = subset.groupby(GROUP).agg(
        true_label=("label", "first"),
        **{
            col: (col, "mean")
            for col in PROB_COLS
        }
    ).reset_index()

    aggregated["predicted_label"] = np.argmax(
        aggregated[PROB_COLS].to_numpy(),
        axis=1
    )

    y_true = aggregated["true_label"]
    y_pred = aggregated["predicted_label"]

    accuracy = accuracy_score(y_true, y_pred)

    balanced = balanced_accuracy_score(
        y_true, y_pred
    )

    macro_f1 = f1_score(
        y_true,
        y_pred,
        labels=CLASSES,
        average="macro"
    )

    summary.append({
        "configuration": name,
        "units": str(selected_units),
        "accuracy": accuracy,
        "balanced_accuracy": balanced,
        "macro_f1": macro_f1,
        "repetitions": len(aggregated)
    })

    print("\n" + "-" * 60)
    print(name)
    print("Sensor units:", selected_units)
    print("Accuracy:", round(accuracy, 4))
    print("Balanced accuracy:", round(balanced, 4))
    print("Macro F1:", round(macro_f1, 4))

    print("\nClass report:")
    print(classification_report(
        y_true,
        y_pred,
        labels=CLASSES,
        target_names=[
            "Correct",
            "Too fast",
            "Low amplitude"
        ],
        zero_division=0
    ))

# --------------------------------------------------
# SAVE COMPARISON
# --------------------------------------------------

result = pd.DataFrame(summary)

result = result.sort_values(
    "macro_f1",
    ascending=False
)

output = (
    ROOT / "data" / "processed"
    / "sensor_fusion_comparison.csv"
)

result.to_csv(output, index=False)

print("\n" + "=" * 65)
print("FINAL SENSOR FUSION COMPARISON")
print("=" * 65)

print(result.to_string(index=False))

print("\nSaved:", output)

print("\nIMPORTANT:")
print("This is exploratory sensor-selection analysis.")
print("Do not treat the best configuration as an unbiased")
print("final result without independent validation.")
