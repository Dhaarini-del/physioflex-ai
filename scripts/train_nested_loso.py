"""
PhysioFlex 3.0 — Nested Leave-One-Subject-Out evaluation.

Run from the project root:
    python scripts/train_nested_loso.py

The script:
- excludes complete repetition groups marked overlaps_previous=True;
- uses numeric sensor features only, excluding IDs, timestamps, labels and flags;
- compares four sensor configurations;
- selects a configuration using inner LOSO on outer-training subjects;
- evaluates the selected configuration on the untouched outer subject;
- reports descriptive outer-fold comparisons for all configurations;
- saves predictions, metrics, confusion matrix, metadata and a final model.

IMPORTANT: With five subjects, results are preliminary and are not clinical validation.
"""

from pathlib import Path
import json
import warnings

import joblib
import numpy as np
import pandas as pd

from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.pipeline import Pipeline

warnings.filterwarnings("ignore", category=UserWarning)

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data" / "processed" / "sensor_features.csv"
OUT = ROOT / "data" / "reports" / "nested_loso"
MODEL_OUT = ROOT / "models"

RANDOM_STATE = 42
N_ESTIMATORS = 500
MIN_SAMPLES_LEAF = 2

GROUP_COLS = ["subject", "exercise", "annotation_row"]
EXCLUDED_COLUMNS = {
    "subject", "exercise", "unit", "annotation_row",
    "start", "end", "segment_length", "duration_seconds",
    "label", "label_name", "overlaps_previous",
}
CONFIGS = {
    "Unit 2": [2],
    "Unit 3": [3],
    "Units 2 + 3": [2, 3],
    "All five units": [1, 2, 3, 4, 5],
}
CLASS_NAMES = {0: "correct", 1: "too_fast", 2: "low_amplitude"}
CLASS_IDS = [0, 1, 2]


def make_pipeline():
    return Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("classifier", RandomForestClassifier(
            n_estimators=N_ESTIMATORS,
            max_features="sqrt",
            min_samples_leaf=MIN_SAMPLES_LEAF,
            class_weight="balanced_subsample",
            random_state=RANDOM_STATE,
            n_jobs=-1,
        )),
    ])


def parse_bool_series(series):
    if pd.api.types.is_bool_dtype(series):
        return series.fillna(False)
    return series.astype(str).str.strip().str.lower().isin(
        {"true", "1", "yes", "y"}
    )


def validate_and_prepare():
    if not INPUT.exists():
        raise FileNotFoundError(f"Dataset not found: {INPUT}")

    df = pd.read_csv(INPUT)
    required = set(GROUP_COLS + ["unit", "label", "overlaps_previous"])
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    df["label"] = pd.to_numeric(df["label"], errors="raise").astype(int)
    df["unit"] = pd.to_numeric(df["unit"], errors="raise").astype(int)

    unexpected = sorted(set(df["label"].unique()) - set(CLASS_IDS))
    if unexpected:
        raise ValueError(f"Unexpected label values: {unexpected}")

    overlap = parse_bool_series(df["overlaps_previous"])
    overlap_groups = df.loc[overlap, GROUP_COLS].drop_duplicates()
    removed_repetitions = len(overlap_groups)

    if removed_repetitions:
        flagged_index = pd.MultiIndex.from_frame(overlap_groups)
        row_index = pd.MultiIndex.from_frame(df[GROUP_COLS])
        keep = ~row_index.isin(flagged_index)
        removed_rows = int((~keep).sum())
        df = df.loc[keep].copy()
    else:
        removed_rows = 0

    grouped = df.groupby(GROUP_COLS, dropna=False)
    mixed_label_groups = int((grouped["label"].nunique() != 1).sum())
    if mixed_label_groups:
        raise ValueError(
            f"{mixed_label_groups} repetitions contain more than one label."
        )

    invalid_groups = []
    for key, part in grouped:
        units = part["unit"].tolist()
        if (
            len(units) != 5
            or len(set(units)) != 5
            or set(units) != {1, 2, 3, 4, 5}
        ):
            invalid_groups.append(key)
            if len(invalid_groups) == 5:
                break
    if invalid_groups:
        raise ValueError(
            "Expected exactly one row from each sensor unit (1–5) per "
            f"repetition. Example invalid groups: {invalid_groups}"
        )

    feature_cols = [
        col for col in df.select_dtypes(include=[np.number]).columns
        if col.lower() not in EXCLUDED_COLUMNS
    ]
    if not feature_cols:
        raise ValueError("No numeric sensor feature columns found.")

    df = df.reset_index(drop=True)

    print("PHYSIOFLEX 3.0 — NESTED LOSO")
    print("=" * 58)
    print(f"Input rows: {len(pd.read_csv(INPUT))}")
    print(f"Excluded overlapping repetitions: {removed_repetitions}")
    print(f"Excluded rows: {removed_rows}")
    print(f"Rows used: {len(df)}")
    print(f"Subjects: {sorted(df['subject'].unique().tolist())}")
    print(f"Repetitions used: {df.groupby(GROUP_COLS).ngroups}")
    print(f"Sensor feature columns: {len(feature_cols)}")
    print("Label counts (sensor rows):")
    print(df["label"].value_counts().sort_index().to_string())
    print()

    return df, feature_cols, removed_repetitions, removed_rows


def subset_units(frame, units):
    return frame.loc[frame["unit"].isin(units)].copy()


def aggregate_repetition_predictions(frame, row_probabilities, model_classes, units):
    """Average sensor-unit probabilities to produce one prediction per repetition."""
    aligned = np.zeros((len(frame), len(CLASS_IDS)), dtype=float)
    for source_col, class_id in enumerate(model_classes):
        aligned[:, CLASS_IDS.index(int(class_id))] = row_probabilities[:, source_col]

    work = frame[GROUP_COLS + ["label", "unit"]].copy().reset_index(drop=True)
    for j, class_id in enumerate(CLASS_IDS):
        work[f"prob_{class_id}"] = aligned[:, j]

    probability_cols = [f"prob_{class_id}" for class_id in CLASS_IDS]
    records = []

    for key, part in work.groupby(GROUP_COLS, sort=False, dropna=False):
        selected = part.loc[part["unit"].isin(units)]
        if (
            len(selected) != len(units)
            or selected["unit"].nunique() != len(units)
            or set(selected["unit"].tolist()) != set(units)
        ):
            continue

        mean_prob = selected[probability_cols].mean(axis=0).to_numpy(dtype=float)
        row = dict(zip(GROUP_COLS, key))
        row["y_true"] = int(selected["label"].iloc[0])
        row["y_pred"] = int(CLASS_IDS[int(np.argmax(mean_prob))])
        for j, class_id in enumerate(CLASS_IDS):
            row[f"prob_{class_id}"] = float(mean_prob[j])
        records.append(row)

    return pd.DataFrame(records)


def fit_and_predict(train_frame, test_frame, feature_cols, units):
    train = subset_units(train_frame, units)
    test = subset_units(test_frame, units)
    if train.empty or test.empty:
        raise ValueError(f"Empty train/test data for sensor units {units}")

    model = make_pipeline()
    model.fit(train[feature_cols], train["label"])

    probabilities = model.predict_proba(test[feature_cols])
    predictions = aggregate_repetition_predictions(
        test,
        probabilities,
        model.named_steps["classifier"].classes_,
        units,
    )

    expected = test.groupby(GROUP_COLS).ngroups
    if len(predictions) != expected:
        raise ValueError(
            f"Predicted {len(predictions)} of {expected} repetitions "
            f"for sensor units {units}."
        )
    return model, predictions


def calculate_metrics(predictions):
    y_true = predictions["y_true"].to_numpy(dtype=int)
    y_pred = predictions["y_pred"].to_numpy(dtype=int)
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, y_pred)),
        "macro_precision": float(precision_score(
            y_true, y_pred, labels=CLASS_IDS,
            average="macro", zero_division=0
        )),
        "macro_recall": float(recall_score(
            y_true, y_pred, labels=CLASS_IDS,
            average="macro", zero_division=0
        )),
        "macro_f1": float(f1_score(
            y_true, y_pred, labels=CLASS_IDS,
            average="macro", zero_division=0
        )),
        "repetitions": int(len(predictions)),
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    MODEL_OUT.mkdir(parents=True, exist_ok=True)

    df, feature_cols, removed_repetitions, removed_rows = validate_and_prepare()
    subjects = sorted(df["subject"].unique().tolist())
    if len(subjects) < 4:
        raise ValueError("Nested LOSO requires at least four subjects.")

    nested_predictions = []
    nested_fold_metrics = []
    inner_selection_rows = []
    comparison_rows = []
    comparison_predictions = []

    for outer_subject in subjects:
        outer_train = df.loc[df["subject"] != outer_subject].copy()
        outer_test = df.loc[df["subject"] == outer_subject].copy()
        inner_subjects = sorted(outer_train["subject"].unique().tolist())

        print(f"Outer test subject: {outer_subject}")
        inner_scores = {}

        # Configuration selection uses only the outer-training subjects.
        for config_name, units in CONFIGS.items():
            fold_scores = []
            for inner_subject in inner_subjects:
                inner_train = outer_train.loc[
                    outer_train["subject"] != inner_subject
                ].copy()
                inner_valid = outer_train.loc[
                    outer_train["subject"] == inner_subject
                ].copy()

                _, inner_pred = fit_and_predict(
                    inner_train, inner_valid, feature_cols, units
                )
                fold_scores.append(calculate_metrics(inner_pred)["macro_f1"])

            mean_score = float(np.mean(fold_scores))
            inner_scores[config_name] = mean_score
            inner_selection_rows.append({
                "outer_test_subject": outer_subject,
                "configuration": config_name,
                "units": ",".join(map(str, units)),
                "inner_mean_macro_f1": mean_score,
                "inner_fold_macro_f1": ";".join(
                    f"{score:.6f}" for score in fold_scores
                ),
            })

        # Prefer fewer units only when inner mean macro-F1 is tied.
        selected_name = max(
            CONFIGS,
            key=lambda name: (inner_scores[name], -len(CONFIGS[name]))
        )
        selected_units = CONFIGS[selected_name]
        print(
            f"  Selected: {selected_name}; "
            f"inner mean macro-F1={inner_scores[selected_name]:.4f}"
        )

        # One untouched outer-subject evaluation for the selected configuration.
        _, outer_pred = fit_and_predict(
            outer_train, outer_test, feature_cols, selected_units
        )
        outer_pred["outer_test_subject"] = outer_subject
        outer_pred["selected_configuration"] = selected_name
        nested_predictions.append(outer_pred)

        nested_fold_metrics.append({
            "outer_test_subject": outer_subject,
            "selected_configuration": selected_name,
            **calculate_metrics(outer_pred),
        })

        # Descriptive comparison: all configurations on the same outer folds.
        for config_name, units in CONFIGS.items():
            _, config_pred = fit_and_predict(
                outer_train, outer_test, feature_cols, units
            )
            config_pred["outer_test_subject"] = outer_subject
            config_pred["configuration"] = config_name
            comparison_predictions.append(config_pred)
            comparison_rows.append({
                "outer_test_subject": outer_subject,
                "configuration": config_name,
                **calculate_metrics(config_pred),
            })

    nested_df = pd.concat(nested_predictions, ignore_index=True)
    fold_df = pd.DataFrame(nested_fold_metrics)
    inner_df = pd.DataFrame(inner_selection_rows)
    comparison_df = pd.DataFrame(comparison_rows)
    comparison_pred_df = pd.concat(comparison_predictions, ignore_index=True)

    nested_df.to_csv(OUT / "nested_loso_outer_predictions.csv", index=False)
    fold_df.to_csv(OUT / "nested_loso_fold_metrics.csv", index=False)
    inner_df.to_csv(OUT / "nested_loso_inner_selection.csv", index=False)
    comparison_df.to_csv(
        OUT / "sensor_configuration_outer_comparison.csv", index=False
    )
    comparison_pred_df.to_csv(
        OUT / "sensor_configuration_outer_predictions.csv", index=False
    )

    overall = calculate_metrics(nested_df)
    pd.DataFrame([overall]).to_csv(
        OUT / "nested_loso_summary.csv", index=False
    )

    cm = confusion_matrix(
        nested_df["y_true"], nested_df["y_pred"], labels=CLASS_IDS
    )
    pd.DataFrame(
        cm,
        index=[f"true_{CLASS_NAMES[c]}" for c in CLASS_IDS],
        columns=[f"pred_{CLASS_NAMES[c]}" for c in CLASS_IDS],
    ).to_csv(OUT / "nested_loso_confusion_matrix.csv")

    # Select a prototype configuration by inner-selection frequency.
    # This is a deployment choice, not a new unbiased performance estimate.
    selected_counts = fold_df["selected_configuration"].value_counts()
    mean_inner = inner_df.groupby("configuration")[
        "inner_mean_macro_f1"
    ].mean().to_dict()
    final_config = max(
        CONFIGS,
        key=lambda name: (
            int(selected_counts.get(name, 0)),
            float(mean_inner.get(name, -1.0)),
            -len(CONFIGS[name]),
        ),
    )
    final_units = CONFIGS[final_config]

    final_model = make_pipeline()
    final_model.fit(
        subset_units(df, final_units)[feature_cols],
        subset_units(df, final_units)["label"],
    )

    artifact = {
        "pipeline": final_model,
        "feature_columns": feature_cols,
        "selected_configuration": final_config,
        "selected_units": final_units,
        "class_names": CLASS_NAMES,
        "group_columns": GROUP_COLS,
        "excluded_overlapping_repetitions": removed_repetitions,
        "excluded_overlapping_rows": removed_rows,
        "evaluation": "nested_leave_one_subject_out",
        "subjects": subjects,
        "warning": (
            "Exploratory evaluation only. Five subjects are insufficient "
            "to establish clinical generalizability; external subject "
            "validation is required."
        ),
    }
    joblib.dump(artifact, MODEL_OUT / "physioflex_movement_rf.joblib")

    metadata = {
        "selected_configuration_for_prototype": final_config,
        "selected_units": final_units,
        "feature_count": len(feature_cols),
        "feature_columns": feature_cols,
        "class_names": CLASS_NAMES,
        "subjects": subjects,
        "excluded_overlapping_repetitions": removed_repetitions,
        "excluded_overlapping_rows": removed_rows,
        "nested_loso_metrics": overall,
        "mean_outer_fold_macro_f1": float(fold_df["macro_f1"].mean()),
        "std_outer_fold_macro_f1": float(fold_df["macro_f1"].std(ddof=1)),
        "limitations": (
            "Only five subjects; preliminary evaluation, not clinical validation."
        ),
    }
    with open(OUT / "model_metadata.json", "w", encoding="utf-8") as handle:
        json.dump(metadata, handle, indent=2)

    print("\n" + "=" * 58)
    print("NESTED LOSO — OUTER OUT-OF-FOLD PERFORMANCE")
    for key, value in overall.items():
        print(f"{key}: {value:.4f}" if isinstance(value, float) else f"{key}: {value}")

    print("\nPER-SUBJECT OUTER FOLD RESULTS")
    print(fold_df.to_string(index=False))

    print("\nDESCRIPTIVE SENSOR CONFIGURATION COMPARISON")
    print(
        comparison_df.groupby("configuration")[
            ["accuracy", "balanced_accuracy", "macro_precision",
             "macro_recall", "macro_f1"]
        ].mean().round(4).to_string()
    )

    print(f"\nPrototype configuration: {final_config} {final_units}")
    print(f"Reports: {OUT}")
    print(f"Model: {MODEL_OUT / 'physioflex_movement_rf.joblib'}")
    print("Reminder: five-subject evaluation is preliminary, not clinical validation.")


if __name__ == "__main__":
    main()
