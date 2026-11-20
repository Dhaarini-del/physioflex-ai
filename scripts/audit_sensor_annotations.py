import csv
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
LABELS = RAW / "labels"

SUBJECTS = range(1, 6)
EXERCISES = range(1, 9)
UNITS = range(1, 6)
VALID_TYPES = {0, 1, 2}


def count_sensor_rows(path):
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.reader(file, delimiter=";")
        next(reader, None)  # Skip header
        return sum(1 for row in reader if row)


def read_annotations(path):
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def main():
    annotation_files = 0
    sensor_files = 0
    missing_files = []
    invalid_intervals = []
    overlapping_intervals = []
    out_of_range = []
    invalid_labels = []
    label_totals = Counter()
    interval_total = 0

    print("PHYSIOFLEX 3.0 - FULL SENSOR ANNOTATION AUDIT")
    print("=" * 55)

    for subject in SUBJECTS:
        for exercise in EXERCISES:
            annotation_path = (
                LABELS
                / f"annotations_s{subject}_e{exercise}_annotations.csv"
            )

            if not annotation_path.exists():
                missing_files.append(str(annotation_path))
                continue

            annotation_files += 1
            annotations = read_annotations(annotation_path)

            parsed = []
            previous_end = 0

            for row_number, row in enumerate(annotations, start=2):
                try:
                    start = int(row["start"])
                    end = int(row["end"])
                    label = int(row["type"])
                except (ValueError, KeyError, TypeError):
                    invalid_intervals.append(
                        f"{annotation_path.name}, CSV row {row_number}: "
                        "unreadable values"
                    )
                    continue

                interval_total += 1

                if start < 0 or end <= start:
                    invalid_intervals.append(
                        f"{annotation_path.name}, row {row_number}: "
                        f"start={start}, end={end}"
                    )

                if start < previous_end:
                    overlapping_intervals.append(
                        f"{annotation_path.name}, row {row_number}: "
                        f"start={start}, previous_end={previous_end}"
                    )

                previous_end = max(previous_end, end)

                if label not in VALID_TYPES:
                    invalid_labels.append(
                        f"{annotation_path.name}, row {row_number}: "
                        f"type={label}"
                    )
                else:
                    label_totals[label] += 1

                parsed.append((start, end, label))

            # Validate this annotation file against all five sensor units.
            for unit in UNITS:
                sensor_path = (
                    RAW
                    / f"s{subject}"
                    / f"e{exercise}"
                    / f"u{unit}"
                    / "test.txt"
                )

                if not sensor_path.exists():
                    missing_files.append(str(sensor_path))
                    continue

                sensor_files += 1
                sensor_rows = count_sensor_rows(sensor_path)

                for start, end, label in parsed:
                    if start < 0 or end > sensor_rows:
                        out_of_range.append(
                            f"s{subject}/e{exercise}/u{unit}: "
                            f"interval [{start}, {end}) exceeds "
                            f"{sensor_rows} rows"
                        )

    print(f"\nAnnotation CSV files found: {annotation_files}/40")
    print(f"Sensor test files found:    {sensor_files}/200")
    print(f"Total annotation intervals: {interval_total}")

    print("\nEXECUTION TYPE COUNTS")
    print("0 - Correct:       ", label_totals[0])
    print("1 - Too fast:      ", label_totals[1])
    print("2 - Low amplitude: ", label_totals[2])

    print("\nVALIDATION RESULTS")
    print("Missing files:          ", len(missing_files))
    print("Invalid intervals:      ", len(invalid_intervals))
    print("Overlapping intervals:  ", len(overlapping_intervals))
    print("Out-of-range intervals: ", len(out_of_range))
    print("Invalid labels:         ", len(invalid_labels))

    problems = (
        missing_files
        + invalid_intervals
        + overlapping_intervals
        + out_of_range
        + invalid_labels
    )

    if problems:
        print("\nISSUES FOUND (first 30)")
        for problem in problems[:30]:
            print("-", problem)

        print("\nAUDIT STATUS: NEEDS INVESTIGATION")
    else:
        print("\nAUDIT STATUS: ALL CHECKS PASSED")

    # Check the expected annotation count for each label.
    print("\nEXPECTED LABEL DISTRIBUTION")
    print("Expected: 400 repetitions per execution type")
    print("Actual:  ", dict(sorted(label_totals.items())))


if __name__ == "__main__":
    main()
