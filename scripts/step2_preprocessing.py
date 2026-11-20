
# ============================================================
# PHYSIOFLEX 3.0
# STEP 2: DATA PREPROCESSING
# ============================================================

import pandas as pd
import numpy as np
from pathlib import Path

# ------------------------------------------------------------
# 1. LOAD DATASET
# ------------------------------------------------------------

# Get the main project directory
PROJECT_DIR = Path(__file__).resolve().parent.parent

# Dataset path
DATA_PATH = PROJECT_DIR / "data" / "processed" / "sensor_features.csv"

print("=" * 60)
print("PHYSIOFLEX 3.0 - DATA PREPROCESSING")
print("=" * 60)

# Check whether dataset exists
if not DATA_PATH.exists():
    raise FileNotFoundError(
        f"Dataset not found: {DATA_PATH}"
    )

# Load CSV dataset
df = pd.read_csv(DATA_PATH)

print("\nDataset loaded successfully!")
print("Dataset shape:", df.shape)


# ------------------------------------------------------------
# 2. DISPLAY DATASET INFORMATION
# ------------------------------------------------------------

print("\nColumn names:")
print(df.columns.tolist())

print("\nFirst 5 records:")
print(df.head())

print("\nDataset information:")
df.info()


# ------------------------------------------------------------
# 3. CHECK REQUIRED COLUMNS
# ------------------------------------------------------------

required_columns = ['subject', 'label_name']

missing_columns = [
    col for col in required_columns
    if col not in df.columns
]

if missing_columns:
    raise ValueError(
        f"Required columns missing: {missing_columns}. "
        "Check the actual column names printed above."
    )

print("\nRequired columns verified!")


# ------------------------------------------------------------
# 4. CHECK MISSING VALUES
# ------------------------------------------------------------

print("\nMissing values in each column:")
print(df.isnull().sum())

total_missing = df.isnull().sum().sum()

print("\nTotal missing values:", total_missing)


# ------------------------------------------------------------
# 5. CHECK DUPLICATE RECORDS
# ------------------------------------------------------------

duplicate_count = df.duplicated().sum()

print("\nDuplicate records:", duplicate_count)


# ------------------------------------------------------------
# 6. CHECK CLASS DISTRIBUTION
# ------------------------------------------------------------

print("\nClass distribution:")

print(
    df['label_name'].value_counts().sort_index()
)


# ------------------------------------------------------------
# 7. CHECK SUBJECT DISTRIBUTION
# ------------------------------------------------------------

print("\nSubject distribution:")

print(
    df['subject'].value_counts().sort_index()
)


# ------------------------------------------------------------
# 8. REMOVE DUPLICATE RECORDS
# ------------------------------------------------------------

df = df.drop_duplicates().copy()

print("\nDuplicates removed.")
print("Dataset shape after duplicate removal:", df.shape)


# ------------------------------------------------------------
# 9. HANDLE MISSING NUMERICAL VALUES
# ------------------------------------------------------------

# Exclude target and subject columns from feature imputation
exclude_columns = ['label_name', 'subject']

feature_columns = [
    col for col in df.columns
    if col not in exclude_columns
]

numeric_features = df[feature_columns].select_dtypes(
    include=np.number
).columns

# Replace infinite values with NaN
df[numeric_features] = df[numeric_features].replace(
    [np.inf, -np.inf], np.nan
)

# Fill missing numerical feature values using median
for col in numeric_features:
    if df[col].isnull().any():
        df[col] = df[col].fillna(df[col].median())

print("\nNumerical missing values handled using median imputation.")


# ------------------------------------------------------------
# 10. FINAL DATASET VALIDATION
# ------------------------------------------------------------

print("\nRemaining missing values:")
print(df.isnull().sum())

print("\nFinal dataset shape:", df.shape)

print("\nFinal class distribution:")
print(df['label_name'].value_counts().sort_index())

print("\nFinal subject distribution:")
print(df['subject'].value_counts().sort_index())


# ------------------------------------------------------------
# 11. SAVE CLEANED DATASET
# ------------------------------------------------------------

OUTPUT_PATH = (
    PROJECT_DIR / "data" / "processed" /
    "sensor_features_cleaned.csv"
)

df.to_csv(OUTPUT_PATH, index=False)

print("\nCleaned dataset saved successfully!")
print("Saved location:", OUTPUT_PATH)


# ------------------------------------------------------------
# COMPLETION
# ------------------------------------------------------------

print("\n" + "=" * 60)
print("STEP 2: DATA PREPROCESSING COMPLETED!")
print("=" * 60)
