
from pathlib import Path
import pandas as pd
from sklearn.metrics import accuracy_score, recall_score

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"

rep = pd.read_csv(DATA / "repetition_loso_predictions.csv")
sensor = pd.read_csv(DATA / "sensor_loso_predictions.csv")

names = {
    0: "Correct",
    1: "Too fast",
    2: "Low amplitude"
}

print("=" * 70)
print("PHYSIOFLEX 3.0 - EXERCISE-WISE ERROR ANALYSIS")
print("=" * 70)

# --------------------------------------------------
# SUBJECT + EXERCISE PERFORMANCE
# --------------------------------------------------

print("\n1. SUBJECT-WISE EXERCISE ACCURACY")
print("-" * 70)

exercise_results = []

for (subject, exercise), group in rep.groupby(
    ["subject", "exercise"]
):
    accuracy = accuracy_score(
        group["true_label"],
        group["predicted_label"]
    )

    exercise_results.append({
        "subject": subject,
        "exercise": exercise,
        "accuracy": accuracy,
        "repetitions": len(group)
    })

exercise_df = pd.DataFrame(exercise_results)

for subject in sorted(exercise_df["subject"].unique()):
    print(f"\nSUBJECT {subject}")

    subset = exercise_df[
        exercise_df["subject"] == subject
    ].sort_values("exercise")

    for _, row in subset.iterrows():
        print(
            f"Exercise {int(row['exercise'])}: "
            f"{row['accuracy']:.2%} "
            f"({int(row['repetitions'])} repetitions)"
        )

# --------------------------------------------------
# SUBJECT + CLASS RECALL
# --------------------------------------------------

print("\n\n2. SUBJECT-WISE CLASS RECALL")
print("-" * 70)

for subject in sorted(rep["subject"].unique()):

    group = rep[rep["subject"] == subject]

    recall = recall_score(
        group["true_label"],
        group["predicted_label"],
        labels=[0, 1, 2],
        average=None,
        zero_division=0
    )

    print(f"\nSubject {subject}")

    for class_id, score in enumerate(recall):
        print(f"{names[class_id]} recall: {score:.2%}")

# --------------------------------------------------
# SENSOR UNIT PERFORMANCE
# --------------------------------------------------

print("\n\n3. SENSOR UNIT ACCURACY BY SUBJECT")
print("-" * 70)

for subject in sorted(sensor["subject"].unique()):

    print(f"\nSubject {subject}")

    group = sensor[sensor["subject"] == subject]

    for unit in sorted(group["unit"].unique()):

        unit_data = group[group["unit"] == unit]

        accuracy = accuracy_score(
            unit_data["label"],
            unit_data["predicted_label"]
        )

        print(
            f"Unit {unit}: {accuracy:.2%} "
            f"({len(unit_data)} records)"
        )

# --------------------------------------------------
# SAVE RESULTS
# --------------------------------------------------

exercise_file = DATA / "exercise_wise_accuracy.csv"

exercise_df.to_csv(exercise_file, index=False)

print("\n" + "=" * 70)
print("DIAGNOSTIC ANALYSIS COMPLETED")
print("=" * 70)
print("Saved:", exercise_file)
