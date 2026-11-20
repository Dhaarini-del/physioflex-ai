import csv
import math
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data" / "processed" / "sensor_manifest.csv"
OUTPUT = ROOT / "data" / "processed" / "sensor_features.csv"

CHANNELS = [
    "acc_x", "acc_y", "acc_z",
    "gyr_x", "gyr_y", "gyr_z",
    "mag_x", "mag_y", "mag_z",
]

SAMPLE_RATE = 25


def quantile(sorted_values, fraction):
    """Linearly interpolated quantile."""
    n = len(sorted_values)

    if n == 1:
        return sorted_values[0]

    position = (n - 1) * fraction
    lower = int(position)
    upper = min(lower + 1, n - 1)
    weight = position - lower

    return (
        sorted_values[lower] * (1 - weight)
        + sorted_values[upper] * weight
    )


def calculate_features(values, prefix):
    n = len(values)

    if n == 0:
        raise ValueError("Cannot extract features from an empty segment")

    mean = math.fsum(values) / n
    variance = math.fsum((x - mean) ** 2 for x in values) / n
    std = math.sqrt(variance)

    ordered = sorted(values)
    rms = math.sqrt(math.fsum(x * x for x in values) / n)
    energy = math.fsum(x * x for x in values)

    differences = [
        values[i] - values[i - 1]
        for i in range(1, n)
    ]

    if differences:
        mean_abs_diff = (
            math.fsum(abs(x) for x in differences)
            / len(differences)
        )
        diff_mean = math.fsum(differences) / len(differences)
        diff_std = math.sqrt(
            math.fsum((x - diff_mean) ** 2 for x in differences)
            / len(differences)
        )
    else:
        mean_abs_diff = 0.0
        diff_std = 0.0

    # Linear trend across the segment
    if n > 1:
        center = (n - 1) / 2
        denominator = math.fsum((i - center) ** 2 for i in range(n))
        slope = math.fsum(
            (i - center) * (values[i] - mean)
            for i in range(n)
        ) / denominator
    else:
        slope = 0.0

    return {
        f"{prefix}_mean": mean,
        f"{prefix}_std": std,
        f"{prefix}_min": ordered[0],
        f"{prefix}_max": ordered[-1],
        f"{prefix}_median": quantile(ordered, 0.50),
        f"{prefix}_q25": quantile(ordered, 0.25),
        f"{prefix}_q75": quantile(ordered, 0.75),
        f"{prefix}_rms": rms,
        f"{prefix}_energy": energy,
        f"{prefix}_mean_abs_diff": mean_abs_diff,
        f"{prefix}_diff_std": diff_std,
        f"{prefix}_slope": slope,
    }


def read_sensor_file(path):
    """Read one sensor recording into nine numeric channels."""
    data = []

    with path.open("r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter=";")

        for row_number, row in enumerate(reader, start=2):
            try:
                values = [float(row[channel]) for channel in CHANNELS]
            except (ValueError, TypeError, KeyError) as exc:
                raise ValueError(
                    f"Invalid sensor value in {path}, row {row_number}: {exc}"
                )

            if not all(math.isfinite(value) for value in values):
                raise ValueError(
                    f"Non-finite sensor value in {path}, row {row_number}"
                )

            data.append(values)

    return data


def add_magnitudes(data):
    """Calculate acceleration, gyroscope and magnetometer magnitudes."""
    result = {
        "acc_mag": [],
        "gyr_mag": [],
        "mag_mag": [],
    }

    for row in data:
        result["acc_mag"].append(
            math.sqrt(sum(x * x for x in row[0:3]))
        )
        result["gyr_mag"].append(
            math.sqrt(sum(x * x for x in row[3:6]))
        )
        result["mag_mag"].append(
            math.sqrt(sum(x * x for x in row[6:9]))
        )

    return result


if not MANIFEST.exists():
    raise FileNotFoundError(
        f"Manifest not found: {MANIFEST}. Build it first."
    )

with MANIFEST.open("r", newline="", encoding="utf-8-sig") as f:
    manifest_rows = list(csv.DictReader(f))

if len(manifest_rows) != 6010:
    raise RuntimeError(
        f"Expected 6010 manifest rows, found {len(manifest_rows)}"
    )

# Group repetitions by their sensor recording.
groups = defaultdict(list)

for record in manifest_rows:
    groups[record["sensor_file"]].append(record)

feature_rows = []
errors = []

print("\nPHYSIOFLEX 3.0 - SENSOR FEATURE EXTRACTION")
print("=" * 48)
print("Manifest records:", len(manifest_rows))
print("Unique sensor recordings:", len(groups))

for file_number, (relative_path, records) in enumerate(
    sorted(groups.items()), start=1
):
    sensor_path = ROOT / relative_path

    if not sensor_path.exists():
        errors.append(f"Missing sensor file: {sensor_path}")
        continue

    try:
        data = read_sensor_file(sensor_path)
        magnitudes = add_magnitudes(data)

        for record in records:
            start = int(record["start"])
            end = int(record["end"])

            if start < 0 or end <= start or end > len(data):
                errors.append(
                    f"Invalid segment {relative_path}: [{start}, {end})"
                )
                continue

            segment = data[start:end]

            if not segment:
                errors.append(
                    f"Empty segment {relative_path}: [{start}, {end})"
                )
                continue

            features = {
                "subject": int(record["subject"]),
                "exercise": int(record["exercise"]),
                "unit": int(record["unit"]),
                "annotation_row": int(record["annotation_row"]),
                "start": start,
                "end": end,
                "segment_length": len(segment),
                "duration_seconds": len(segment) / SAMPLE_RATE,
                "label": int(record["label"]),
                "label_name": record["label_name"],
                "overlaps_previous": record["overlaps_previous"],
            }

            for channel_index, channel in enumerate(CHANNELS):
                values = [
                    row[channel_index] for row in segment
                ]
                features.update(
                    calculate_features(values, channel)
                )

            for magnitude_name, values in magnitudes.items():
                features.update(
                    calculate_features(
                        values[start:end],
                        magnitude_name
                    )
                )

            feature_rows.append(features)

    except Exception as exc:
        errors.append(f"{relative_path}: {exc}")

    if file_number % 20 == 0:
        print(
            f"Processed {file_number}/{len(groups)} sensor recordings"
        )

if feature_rows:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=list(feature_rows[0].keys())
        )
        writer.writeheader()
        writer.writerows(feature_rows)

print("\nEXTRACTION RESULTS")
print("=" * 48)
print("Feature records:", len(feature_rows))
print("Expected records:", len(manifest_rows))
print("Errors:", len(errors))

if errors:
    print("\nERROR DETAILS")
    for error in errors[:30]:
        print("-", error)
    if len(errors) > 30:
        print("Additional errors:", len(errors) - 30)

print("\nOUTPUT:")
print(OUTPUT)

if len(feature_rows) == len(manifest_rows) and not errors:
    print("\nSUCCESS: All sensor segments have feature records.")
else:
    print("\nWARNING: Investigate errors before model training.")
