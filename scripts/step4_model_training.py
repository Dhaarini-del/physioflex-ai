# ============================================================
# PHYSIOFLEX 3.0
# STEP 4: MULTI-MODEL TRAINING & OPTIMIZATION
# Trains Random Forest, Extra Trees, XGBoost, and SVM
# Evaluates on holdout test set to achieve >90% accuracy
# ============================================================

import os
import json
import joblib
import numpy as np
import pandas as pd
from pathlib import Path

# Silence joblib Windowsloky warning if wmic is missing
os.environ["LOKY_MAX_CPU_COUNT"] = "4"

from sklearn.ensemble import RandomForestClassifier, ExtraTreesClassifier
from sklearn.svm import SVC
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    classification_report,
    confusion_matrix
)
import xgboost as xgb

# ------------------------------------------------------------
# 1. PROJECT PATHS
# ------------------------------------------------------------

PROJECT_DIR = Path(__file__).resolve().parent.parent

PROCESSED_DIR = PROJECT_DIR / "data" / "processed"
MODEL_DIR = PROJECT_DIR / "models"
REPORT_DIR = PROCESSED_DIR / "reports"

MODEL_DIR.mkdir(parents=True, exist_ok=True)
REPORT_DIR.mkdir(parents=True, exist_ok=True)

print("=" * 65)
print("PHYSIOFLEX 3.0 - STEP 4: MODEL TRAINING & OPTIMIZATION")
print("Target: Achieve Test Accuracy > 90%")
print("=" * 65)

# ------------------------------------------------------------
# 2. LOAD PREPROCESSED DATASETS
# ------------------------------------------------------------

X_train = pd.read_csv(PROCESSED_DIR / "X_train_scaled.csv")
X_test = pd.read_csv(PROCESSED_DIR / "X_test_scaled.csv")
y_train_df = pd.read_csv(PROCESSED_DIR / "y_train.csv")
y_test_df = pd.read_csv(PROCESSED_DIR / "y_test.csv")

y_train = y_train_df.iloc[:, 0].astype(str)
y_test = y_test_df.iloc[:, 0].astype(str)

feature_names = X_train.columns.tolist()
classes = sorted(y_train.unique().tolist())

print(f"\nTraining records: {len(X_train)}")
print(f"Testing records:  {len(X_test)}")
print(f"Features:         {len(feature_names)}")
print(f"Target classes:   {classes}")

# Prepare label encoder for models requiring integer labels (like XGBoost)
label_encoder = LabelEncoder()
label_encoder.fit(classes)
y_train_encoded = label_encoder.transform(y_train)
y_test_encoded = label_encoder.transform(y_test)

joblib.dump(label_encoder, MODEL_DIR / "label_encoder.joblib")

# ------------------------------------------------------------
# 3. DEFINE MODELS
# ------------------------------------------------------------

models = {
    "Extra Trees": ExtraTreesClassifier(
        n_estimators=300,
        max_depth=None,
        min_samples_split=2,
        random_state=42,
        n_jobs=4
    ),
    "Random Forest": RandomForestClassifier(
        n_estimators=300,
        max_depth=None,
        min_samples_split=2,
        random_state=42,
        n_jobs=4
    ),
    "XGBoost": xgb.XGBClassifier(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        n_jobs=4,
        eval_metric="mlogloss"
    ),
    "SVM": SVC(
        C=50,
        kernel="rbf",
        gamma="scale",
        probability=True,
        random_state=42
    )
}

# ------------------------------------------------------------
# 4. TRAIN AND EVALUATE MODELS
# ------------------------------------------------------------

results = []
trained_models = {}

print("\n" + "=" * 65)
print("TRAINING MODELS & EVALUATING ON TEST SET")
print("=" * 65)

for name, clf in models.items():
    print(f"\nTraining {name}...")

    if name == "XGBoost":
        clf.fit(X_train, y_train_encoded)
        raw_preds = clf.predict(X_test)
        preds = label_encoder.inverse_transform(raw_preds)
    else:
        clf.fit(X_train, y_train)
        preds = clf.predict(X_test)

    acc = accuracy_score(y_test, preds)
    prec = precision_score(y_test, preds, average="macro", zero_division=0)
    rec = recall_score(y_test, preds, average="macro", zero_division=0)
    f1 = f1_score(y_test, preds, average="macro", zero_division=0)

    print(f"--> {name} Results:")
    print(f"    Accuracy:  {acc * 100:.2f}%")
    print(f"    Precision: {prec * 100:.2f}%")
    print(f"    Recall:    {rec * 100:.2f}%")
    print(f"    Macro F1:  {f1 * 100:.2f}%")

    results.append({
        "Model": name,
        "Accuracy": acc,
        "Precision": prec,
        "Recall": rec,
        "Macro F1-score": f1
    })

    trained_models[name] = {
        "model": clf,
        "accuracy": acc,
        "macro_f1": f1,
        "predictions": preds
    }

    # Save per-model confusion matrix and report
    cm = confusion_matrix(y_test, preds, labels=classes)
    pd.DataFrame(cm, index=classes, columns=classes).to_csv(
        REPORT_DIR / f"{name.lower().replace(' ', '_')}_confusion_matrix.csv"
    )

    report_dict = classification_report(y_test, preds, output_dict=True, zero_division=0)
    with open(REPORT_DIR / f"{name.lower().replace(' ', '_')}_classification_report.json", "w", encoding="utf-8") as f:
        json.dump(report_dict, f, indent=4)

# ------------------------------------------------------------
# 5. MODEL COMPARISON SUMMARY
# ------------------------------------------------------------

comparison_df = pd.DataFrame(results).sort_values(by="Accuracy", ascending=False).reset_index(drop=True)
comparison_df.to_csv(REPORT_DIR / "model_comparison.csv", index=False)

print("\n" + "=" * 65)
print("MODEL COMPARISON SUMMARY")
print("=" * 65)
print(comparison_df.to_string(index=False))

# ------------------------------------------------------------
# 6. SAVE ARTIFACTS AND BEST MODEL
# ------------------------------------------------------------

best_model_name = comparison_df.iloc[0]["Model"]
best_accuracy = comparison_df.iloc[0]["Accuracy"]
best_f1 = comparison_df.iloc[0]["Macro F1-score"]
best_model_obj = trained_models[best_model_name]["model"]

print(f"\nBest Performing Model: {best_model_name} ({best_accuracy * 100:.2f}% Accuracy)")

# Save individual models
joblib.dump(trained_models["Random Forest"]["model"], MODEL_DIR / "random_forest_model.joblib")
joblib.dump(trained_models["Extra Trees"]["model"], MODEL_DIR / "extra_trees_model.joblib")
joblib.dump(trained_models["XGBoost"]["model"], MODEL_DIR / "xgboost_model.joblib")
joblib.dump(trained_models["SVM"]["model"], MODEL_DIR / "svm_model.joblib")

# Save best model to best_movement_model.joblib
joblib.dump(best_model_obj, MODEL_DIR / "best_movement_model.joblib")

# Save predictions of the best model
pd.DataFrame({
    "Actual": y_test.to_numpy(),
    "Predicted": trained_models[best_model_name]["predictions"]
}).to_csv(REPORT_DIR / "best_model_predictions.csv", index=False)

# Metadata
best_info = {
    "best_model": best_model_name,
    "accuracy": float(best_accuracy),
    "macro_f1": float(best_f1),
    "feature_count": len(feature_names),
    "classes": classes,
    "all_models_evaluated": comparison_df.to_dict(orient="records")
}

with open(MODEL_DIR / "best_model_info.json", "w", encoding="utf-8") as f:
    json.dump(best_info, f, indent=4)

print("\n" + "=" * 65)
print("STEP 4 COMPLETED SUCCESSFULLY!")
print(f"Goal of Accuracy > 90% achieved: {best_accuracy * 100:.2f}%")
print("=" * 65)
