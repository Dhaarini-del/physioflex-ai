from pathlib import Path
import argparse
import json
import joblib
import pandas as pd

from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix

def main():
    parser = argparse.ArgumentParser(description="Train a grouped Random Forest movement baseline.")
    parser.add_argument("--features", default="data/features/movement_features_video_summary.csv")
    parser.add_argument("--labels", default="data/annotations/movement_labels.csv")
    parser.add_argument("--output", default="models/movement_classifier.joblib")
    args = parser.parse_args()

    feature_path, label_path = Path(args.features), Path(args.labels)
    if not feature_path.exists() or not label_path.exists():
        raise SystemExit("Feature or label file not found. Run extraction and complete annotations first.")

    features = pd.read_csv(feature_path)
    labels = pd.read_csv(label_path)

    required_labels = {"video_id", "movement_label"}
    if not required_labels.issubset(labels.columns):
        raise SystemExit(f"Labels must contain columns: {sorted(required_labels)}")

    labels["movement_label"] = labels["movement_label"].astype(str).str.strip().str.lower()
    labels = labels[labels["movement_label"].isin(["correct", "incorrect", "uncertain"])]
    labels = labels[labels["movement_label"] != "uncertain"]

    data = features.merge(labels[["video_id", "movement_label"]], on="video_id", how="inner")
    if data.empty:
        raise SystemExit("No matching labeled videos. Ensure video_id values match the feature summary.")

    # This starter uses video_id as the group. For patient-level claims,
    # replace this with a patient_id grouping column and patient-separated split.
    if data["movement_label"].nunique() < 2:
        raise SystemExit("At least two labeled classes are required for classification.")
    if data["video_id"].nunique() < 5:
        raise SystemExit("Too few distinct videos for this starter split. Collect more reviewed examples.")

    excluded = {"video_id", "movement_label"}
    feature_cols = [c for c in data.columns if c not in excluded]
    X = data[feature_cols].apply(pd.to_numeric, errors="coerce")
    y = data["movement_label"]
    groups = data["video_id"]

    splitter = GroupShuffleSplit(n_splits=1, test_size=0.25, random_state=42)
    train_idx, test_idx = next(splitter.split(X, y, groups=groups))
    X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
    y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]

    if y_train.nunique() < 2:
        raise SystemExit("Training split contains only one class. Add more balanced labeled videos and retry.")

    model = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("classifier", RandomForestClassifier(
            n_estimators=300,
            class_weight="balanced",
            random_state=42,
            min_samples_leaf=2
        ))
    ])
    model.fit(X_train, y_train)
    predictions = model.predict(X_test)

    report = classification_report(y_test, predictions, output_dict=True, zero_division=0)
    print("Classification report:")
    print(classification_report(y_test, predictions, zero_division=0))
    print("Confusion matrix:")
    print(confusion_matrix(y_test, predictions, labels=sorted(y.unique())))

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({
        "model": model,
        "feature_columns": feature_cols,
        "classes": list(model.classes_),
        "model_type": "RandomForestClassifier",
        "split_group": "video_id",
        "warning": "Research prototype; not clinically validated."
    }, output)

    report_path = output.with_suffix(".metrics.json")
    report_path.write_text(json.dumps({
        "classification_report": report,
        "test_video_count": int(groups.iloc[test_idx].nunique()),
        "train_video_count": int(groups.iloc[train_idx].nunique()),
        "features": feature_cols
    }, indent=2), encoding="utf-8")

    print(f"Saved model: {output.resolve()}")
    print(f"Saved metrics: {report_path.resolve()}")

if __name__ == "__main__":
    main()
