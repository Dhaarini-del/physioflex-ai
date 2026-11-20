from pathlib import Path
import pandas as pd
from sklearn.metrics import classification_report, confusion_matrix

ROOT = Path(__file__).resolve().parents[1]

FILE = ROOT / "data" / "processed" / "repetition_loso_predictions.csv"

df = pd.read_csv(FILE)

names = {
    0: "Correct",
    1: "Too fast",
    2: "Low amplitude"
}

print("=" * 65)
print("PHYSIOFLEX 3.0 - SUBJECT-WISE ERROR ANALYSIS")
print("=" * 65)

for subject in sorted(df["subject"].unique()):

    data = df[df["subject"] == subject]

    print("\n" + "=" * 55)
    print(f"SUBJECT {subject}")
    print("Repetitions:", len(data))
    print("=" * 55)

    print("\nClass distribution:")
    print(data["true_label"].map(names).value_counts())

    print("\nClassification report:")

    print(classification_report(
        data["true_label"],
        data["predicted_label"],
        labels=[0, 1, 2],
        target_names=[names[i] for i in [0, 1, 2]],
        zero_division=0
    ))

    print("Confusion matrix:")
    print(confusion_matrix(
        data["true_label"],
        data["predicted_label"],
        labels=[0, 1, 2]
    ))

print("\nAnalysis completed.")
