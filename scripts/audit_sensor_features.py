import csv
import math
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FEATURE_FILE = ROOT / "data" / "processed" / "sensor_features.csv"

EXPECTED_ROWS = 6010
METADATA_COLUMNS = {
    "subject", "exercise", "unit", "annotation_row",
    "start", "end", "segment_length", "duration_seconds",
    "label", "label_name", "overlaps_previous",
}

with FEATURE_FILE.open("r", newline="", encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)
    rows = list(reader)
    columns = reader.fieldnames or []

print("\nPHYSIOFLEX 3.0 - FEATURE QUALITY AUDIT")
print("=" * 48)

errors = []

if len(rows) != EXPECTED_ROWS:
    errors.append(f"Expected {EXPECTED_ROWS} rows, found {len(rows)}")

feature_columns = [
    col for col in columns if col not in METADATA_COLUMNS
]

if not feature_columns:
    errors.append("No numerical feature columns found")

print("Feature records:", len(rows))
print("Metadata columns:", len(METADATA_COLUMNS))
print("Numerical feature columns:", len(feature_columns))

# Check numeric values for missing, invalid and non-finite values.
missing_values = 0
invalid_values = 0
non_finite_values = 0

for row_number, row in enumerate(rows, start=2):
    for col in feature_columns:
        value = row.get(col, "")

        if value is None or value.strip() == "":
            missing_values += 1
            continue

        try:
            number = float(value)
            if not math.isfinite(number):
                non_finite_values += 1
        except ValueError:
            invalid_values += 1

print("\nNUMERICAL VALIDATION")
print("Missing feature values:", missing_values)
print("Invalid numerical values:", invalid_values)
print("Infinite or NaN values:", non_finite_values)

if missing_values or invalid_values or non_finite_values:
    errors.append("Numerical validation failed")

# Check labels and their distributions.
class_counts = Counter()
subject_counts = Counter()
unit_counts = Counter()
exercise_counts = Counter()
segment_keys = Counter()
repetition_units = defaultdict(set)

for row in rows:
    try:
        subject = int(row["subject"])
        exercise = int(row["exercise"])
        unit = int(row["unit"])
        annotation_row = int(row["annotation_row"])
        label = int(row["label"])
        start = int(row["start"])
        end = int(row["end"])

        if label not in (0, 1, 2):
            errors.append(f"Unexpected label: {label}")

        if end <= start:
            errors.append(
                f"Invalid interval: subject={subject}, exercise={exercise}"
            )

        key = (subject, exercise, unit, annotation_row)
        segment_keys[key] += 1

        repetition_key = (subject, exercise, annotation_row)
        repetition_units[repetition_key].add(unit)

        class_counts[label] += 1
        subject_counts[subject] += 1
        unit_counts[unit] += 1
        exercise_counts[exercise] += 1

    except (ValueError, KeyError) as exc:
        errors.append(f"Invalid metadata row: {exc}")

duplicates = sum(
    count - 1 for count in segment_keys.values() if count > 1
)

incomplete_repetitions = sum(
    1 for units in repetition_units.values() if len(units) != 5
)

print("\nLABEL COUNTS (SENSOR-UNIT RECORDS)")
for label, name in [
    (0, "Correct"),
    (1, "Too fast"),
    (2, "Low amplitude"),
]:
    print(f"{label} - {name}: {class_counts[label]}")

print("\nSUBJECT RECORD COUNTS")
for subject in sorted(subject_counts):
    print(f"Subject {subject}: {subject_counts[subject]}")

print("\nSENSOR UNIT RECORD COUNTS")
for unit in sorted(unit_counts):
    print(f"Unit {unit}: {unit_counts[unit]}")

print("\nEXERCISE RECORD COUNTS")
for exercise in sorted(exercise_counts):
    print(f"Exercise {exercise}: {exercise_counts[exercise]}")

print("\nSTRUCTURAL VALIDATION")
print("Duplicate segment records:", duplicates)
print("Incomplete five-unit repetitions:", incomplete_repetitions)

overlap_records = sum(
    1 for row in rows
    if row.get("overlaps_previous", "").lower() == "true"
)

print("Rows flagged for annotation overlap:", overlap_records)

if duplicates:
    errors.append("Duplicate segment records found")

if incomplete_repetitions:
    errors.append("Some repetitions do not have five sensor units")

# Report duration range.
durations = [
    float(row["duration_seconds"])
    for row in rows
    if row.get("duration_seconds")
]

if durations:
    print("\nSEGMENT DURATION")
    print("Minimum:", round(min(durations), 3), "seconds")
    print("Maximum:", round(max(durations), 3), "seconds")
    print("Average:", round(sum(durations) / len(durations), 3), "seconds")

print("\nFINAL RESULT")
print("=" * 48)

if errors:
    print("AUDIT FAILED")
    for error in errors[:30]:
        print("-", error)
    if len(errors) > 30:
        print("Additional errors:", len(errors) - 30)
else:
    print("AUDIT PASSED")
    print("All feature records passed structural and numerical checks.")
