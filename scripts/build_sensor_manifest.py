import csv
import re
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
LABEL_DIR = RAW / "labels"
OUTPUT_DIR = ROOT / "data" / "processed"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

MANIFEST_PATH = OUTPUT_DIR / "sensor_manifest.csv"
QUALITY_PATH = OUTPUT_DIR / "annotation_quality_report.csv"

LABEL_NAMES = {
    0: "correct",
    1: "too_fast",
    2: "low_amplitude",
}

manifest = []
quality = []
errors = []

label_files = sorted(LABEL_DIR.glob("annotations_s*_e*_annotations.csv"))

if len(label_files) != 40:
    raise RuntimeError(
        f"Expected 40 annotation CSV files, found {len(label_files)}"
    )

for label_file in label_files:
    match = re.fullmatch(
        r"annotations_s(\d+)_e(\d+)_annotations\.csv",
        label_file.name
    )

    if not match:
        errors.append(f"Unexpected annotation filename: {label_file.name}")
        continue

    subject = int(match.group(1))
    exercise = int(match.group(2))

    with label_file.open("r", newline="", encoding="utf-8-sig") as f:
        annotations = list(csv.DictReader(f))

    intervals = []

    for row_number, row in enumerate(annotations, start=2):
        try:
            start = int(row["start"])
            end = int(row["end"])
            label = int(row["type"])
        except (ValueError, KeyError, TypeError):
            errors.append(
                f"{label_file.name}, row {row_number}: invalid values"
            )
            continue

        if start < 0 or end <= start or label not in LABEL_NAMES:
            errors.append(
                f"{label_file.name}, row {row_number}: "
                f"invalid interval or label"
            )
            continue

        intervals.append({
            "annotation_row": row_number,
            "start": start,
            "end": end,
            "label": label,
        })

    intervals.sort(key=lambda x: (x["start"], x["end"]))

    previous_end = -1
    overlap_count = 0
    class_counts = Counter()

    # Verify all five sensor-unit recordings.
    unit_rows = {}

    for unit in range(1, 6):
        sensor_file = (
            RAW / f"s{subject}" / f"e{exercise}" /
            f"u{unit}" / "test.txt"
        )

        if not sensor_file.exists():
            errors.append(f"Missing sensor file: {sensor_file}")
            continue

        with sensor_file.open(
            "r", newline="", encoding="utf-8-sig"
        ) as f:
            reader = csv.reader(f, delimiter=";")
            header = next(reader, None)
            row_count = sum(1 for _ in reader)

        expected_header = [
            "time index",
            "acc_x", "acc_y", "acc_z",
            "gyr_x", "gyr_y", "gyr_z",
            "mag_x", "mag_y", "mag_z",
        ]

        if header != expected_header:
            errors.append(f"Unexpected sensor columns: {sensor_file}")
            continue

        unit_rows[unit] = row_count

    for interval in intervals:
        start = interval["start"]
        end = interval["end"]
        label = interval["label"]

        overlaps_previous = start < previous_end

        if overlaps_previous:
            overlap_count += 1

        previous_end = max(previous_end, end)
        class_counts[label] += 1

        for unit, row_count in unit_rows.items():
            if end > row_count:
                errors.append(
                    f"Out-of-range interval: s{subject}/e{exercise}/"
                    f"u{unit}, [{start}, {end}), rows={row_count}"
                )
                continue

            manifest.append({
                "subject": subject,
                "exercise": exercise,
                "unit": unit,
                "annotation_row": interval["annotation_row"],
                "start": start,
                "end": end,
                "segment_length": end - start,
                "duration_seconds": round((end - start) / 25, 4),
                "label": label,
                "label_name": LABEL_NAMES[label],
                "sensor_file": str(
                    Path("data") / "raw" /
                    f"s{subject}" / f"e{exercise}" /
                    f"u{unit}" / "test.txt"
                ),
                "overlaps_previous": overlaps_previous,
            })

    quality.append({
        "subject": subject,
        "exercise": exercise,
        "annotation_file": label_file.name,
        "annotation_count": len(intervals),
        "correct_count": class_counts[0],
        "too_fast_count": class_counts[1],
        "low_amplitude_count": class_counts[2],
        "overlap_count": overlap_count,
        "sensor_units_found": len(unit_rows),
    })


def write_csv(path, rows):
    if not rows:
        return

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


write_csv(MANIFEST_PATH, manifest)
write_csv(QUALITY_PATH, quality)

print("\nPHYSIOFLEX 3.0 - SENSOR MANIFEST BUILD")
print("=" * 48)
print("Annotation files:", len(label_files))
print("Subject/exercise quality records:", len(quality))
print("Manifest rows:", len(manifest))
print("Expected rows:", 1202 * 5)
print("Errors:", len(errors))

print("\nCLASS COUNTS (ANNOTATIONS)")
total_classes = Counter()
for item in quality:
    total_classes[0] += item["correct_count"]
    total_classes[1] += item["too_fast_count"]
    total_classes[2] += item["low_amplitude_count"]

for label, name in LABEL_NAMES.items():
    print(f"{label} - {name}: {total_classes[label]}")

print("\nOVERLAP COUNT:", sum(x["overlap_count"] for x in quality))

print("\nOUTPUT FILES")
print(MANIFEST_PATH)
print(QUALITY_PATH)

if errors:
    print("\nERROR DETAILS")
    for error in errors[:30]:
        print("-", error)
    if len(errors) > 30:
        print(f"... and {len(errors) - 30} more errors")
else:
    print("\nAll manifest checks passed.")
