# ============================================================
# PHYSIOFLEX 3.0
# STEP 3: FEATURE SELECTION AND TRAIN-TEST SPLITTING
# ============================================================

import pandas as pd
import numpy as np
import json
import joblib

from pathlib import Path
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split


# ------------------------------------------------------------
# 1. PROJECT PATHS
# ------------------------------------------------------------

PROJECT_DIR = Path(__file__).resolve().parent.parent

DATA_PATH = (
    PROJECT_DIR / "data" / "processed" /
    "sensor_features_cleaned.csv"
)

OUTPUT_DIR = PROJECT_DIR / "data" / "processed"
MODEL_DIR = PROJECT_DIR / "models"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
MODEL_DIR.mkdir(parents=True, exist_ok=True)


print("=" * 65)
print("PHYSIOFLEX 3.0 - STEP 3")
print("FEATURE SELECTION AND STRATIFIED TRAIN-TEST SPLITTING")
print("=" * 65)


# ------------------------------------------------------------
# 2. LOAD CLEANED DATASET
# ------------------------------------------------------------

if not DATA_PATH.exists():
    raise FileNotFoundError(
        f"Dataset not found: {DATA_PATH}"
    )

df = pd.read_csv(DATA_PATH)

print("\nDataset loaded successfully!")
print("Dataset shape:", df.shape)


# ------------------------------------------------------------
# 3. CHECK REQUIRED COLUMNS
# ------------------------------------------------------------

required_columns = ["subject", "label_name"]

for col in required_columns:
    if col not in df.columns:
        raise ValueError(
            f"Required column '{col}' not found!"
        )

if df["subject"].isnull().any():
    raise ValueError("Subject column contains missing values.")

if df["label_name"].isnull().any():
    raise ValueError("Target column contains missing labels.")

print("\nRequired columns verified!")


# ------------------------------------------------------------
# 4. STRATIFIED TRAIN-TEST SPLIT (80% TRAIN, 20% TEST)
# ------------------------------------------------------------

train_df, test_df = train_test_split(
    df,
    test_size=0.20,
    random_state=42,
    stratify=df["label_name"]
)

train_df = train_df.copy().reset_index(drop=True)
test_df = test_df.copy().reset_index(drop=True)

print("\nStratified 80/20 train-test splitting completed!")
print("Training records:", len(train_df))
print("Testing records:", len(test_df))
print("Training subjects:", sorted(train_df["subject"].unique()))
print("Testing subjects:", sorted(test_df["subject"].unique()))


# ------------------------------------------------------------
# 5. SELECT NUMERICAL SENSOR FEATURES
# ------------------------------------------------------------

# Columns that must not be used as input features
excluded_columns = [
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
    "overlaps_previous"
]

numeric_columns = df.select_dtypes(
    include=[np.number]
).columns.tolist()

feature_columns = [
    col for col in numeric_columns
    if col not in excluded_columns
]

if not feature_columns:
    raise ValueError("No numerical sensor features found!")

print("\nFeature selection completed!")
print("Total dataset columns:", len(df.columns))
print("Selected sensor features:", len(feature_columns))


# ------------------------------------------------------------
# 6. CREATE INPUT FEATURES (X) AND TARGET (y)
# ------------------------------------------------------------

X_train = train_df[feature_columns].copy()
X_test = test_df[feature_columns].copy()

y_train = train_df["label_name"].copy()
y_test = test_df["label_name"].copy()

print("\nInput and target separation completed!")
print("X_train shape:", X_train.shape)
print("X_test shape:", X_test.shape)
print("y_train shape:", y_train.shape)
print("y_test shape:", y_test.shape)


# ------------------------------------------------------------
# 7. CHECK CLASS DISTRIBUTION
# ------------------------------------------------------------

print("\nTraining class distribution:")
print(y_train.value_counts().sort_index())

print("\nTesting class distribution:")
print(y_test.value_counts().sort_index())


# ------------------------------------------------------------
# 8. CHECK INVALID FEATURE VALUES
# ------------------------------------------------------------

X_train = X_train.replace([np.inf, -np.inf], np.nan)
X_test = X_test.replace([np.inf, -np.inf], np.nan)

valid_features = [
    col for col in feature_columns
    if X_train[col].notna().any()
]

X_train = X_train[valid_features]
X_test = X_test[valid_features]
feature_columns = valid_features


# ------------------------------------------------------------
# 9. IMPUTE AND SCALE FEATURES
# ------------------------------------------------------------

preprocessing_pipeline = Pipeline([
    ("imputer", SimpleImputer(strategy="median")),
    ("scaler", StandardScaler())
])

X_train_scaled = preprocessing_pipeline.fit_transform(X_train)
X_test_scaled = preprocessing_pipeline.transform(X_test)

print("\nFeature scaling completed!")
print("Scaled training shape:", X_train_scaled.shape)
print("Scaled testing shape:", X_test_scaled.shape)


# ------------------------------------------------------------
# 10. SAVE PROCESSED DATASETS
# ------------------------------------------------------------

X_train_scaled_df = pd.DataFrame(
    X_train_scaled,
    columns=feature_columns
)

X_test_scaled_df = pd.DataFrame(
    X_test_scaled,
    columns=feature_columns
)

X_train_scaled_df.to_csv(
    OUTPUT_DIR / "X_train_scaled.csv",
    index=False
)

X_test_scaled_df.to_csv(
    OUTPUT_DIR / "X_test_scaled.csv",
    index=False
)

y_train.to_csv(
    OUTPUT_DIR / "y_train.csv",
    index=False,
    header=["label_name"]
)

y_test.to_csv(
    OUTPUT_DIR / "y_test.csv",
    index=False,
    header=["label_name"]
)

# Save unscaled raw test samples for final API testing (Step 7)
test_df.to_csv(
    OUTPUT_DIR / "test_raw_samples.csv",
    index=False
)


# ------------------------------------------------------------
# 11. SAVE PREPROCESSING PIPELINE & FEATURE LIST
# ------------------------------------------------------------

joblib.dump(
    preprocessing_pipeline,
    MODEL_DIR / "feature_preprocessing_pipeline.joblib"
)

with open(MODEL_DIR / "selected_features.json", "w", encoding="utf-8") as file:
    json.dump(feature_columns, file, indent=4)


# ------------------------------------------------------------
# 12. SAVE SPLIT SUMMARY
# ------------------------------------------------------------

split_summary = {
    "split_strategy": "stratified_train_test_split",
    "test_size": 0.20,
    "random_state": 42,
    "training_records": len(X_train),
    "testing_records": len(X_test),
    "selected_feature_count": len(feature_columns),
    "classes": sorted(y_train.unique().tolist()),
    "training_subjects": sorted(train_df["subject"].unique().tolist()),
    "testing_subjects": sorted(test_df["subject"].unique().tolist())
}

with open(OUTPUT_DIR / "split_summary.json", "w", encoding="utf-8") as file:
    json.dump(split_summary, file, indent=4)


print("\n" + "=" * 65)
print("STEP 3 COMPLETED SUCCESSFULLY!")
print("=" * 65)
print(f"Training records: {len(X_train)}")
print(f"Testing records:  {len(X_test)}")
print(f"Selected features: {len(feature_columns)}")
print("\nAll files saved successfully!")
print("=" * 65)
