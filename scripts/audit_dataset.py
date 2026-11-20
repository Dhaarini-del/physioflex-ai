from pathlib import Path
import argparse
import csv

VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".webm", ".mpeg", ".mpg"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}
METADATA_EXTENSIONS = {".csv", ".json", ".txt", ".xml", ".yaml", ".yml"}

def main():
    parser = argparse.ArgumentParser(description="Inventory a rehabilitation dataset.")
    parser.add_argument("--input", default="data/raw")
    parser.add_argument("--output", default="data/reports/dataset_audit.csv")
    args = parser.parse_args()

    source = Path(args.input)
    output = Path(args.output)
    if not source.exists():
        raise SystemExit(f"Input folder does not exist: {source.resolve()}")

    rows = []
    for path in source.rglob("*"):
        if not path.is_file():
            continue
        ext = path.suffix.lower()
        if ext in VIDEO_EXTENSIONS:
            kind = "video"
        elif ext in IMAGE_EXTENSIONS:
            kind = "image"
        elif ext in METADATA_EXTENSIONS:
            kind = "metadata_or_annotation"
        else:
            continue
        rows.append({
            "video_id": path.stem if kind == "video" else "",
            "filename": path.name,
            "relative_path": str(path.relative_to(source)),
            "file_type": kind,
            "extension": ext,
            "size_mb": round(path.stat().st_size / (1024 * 1024), 3),
        })

    output.parent.mkdir(parents=True, exist_ok=True)
    fields = ["video_id", "filename", "relative_path", "file_type", "extension", "size_mb"]
    with output.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    counts = {}
    for row in rows:
        counts[row["file_type"]] = counts.get(row["file_type"], 0) + 1
    print(f"Files inventoried: {len(rows)}")
    print(f"Counts: {counts}")
    print(f"Audit saved: {output.resolve()}")

if __name__ == "__main__":
    main()
