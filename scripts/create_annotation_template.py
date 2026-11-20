from pathlib import Path
import argparse
import pandas as pd

def main():
    parser = argparse.ArgumentParser(description="Create a blank human-review annotation CSV.")
    parser.add_argument("--input", default="data/reports/dataset_audit.csv")
    parser.add_argument("--output", default="data/annotations/movement_labels.csv")
    args = parser.parse_args()

    audit = pd.read_csv(args.input)
    if "file_type" not in audit.columns or "filename" not in audit.columns:
        raise SystemExit("Audit CSV must contain file_type and filename columns.")

    videos = audit[audit["file_type"] == "video"].copy()
    if videos.empty:
        raise SystemExit("No videos found in the audit CSV.")

    rows = pd.DataFrame({
        "video_id": videos["video_id"].astype(str),
        "filename": videos["filename"].astype(str),
        "exercise": "",
        "movement_label": "",
        "error_type": "",
        "reviewer": "",
        "review_date": "",
        "notes": "",
    })
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    rows.to_csv(output, index=False)
    print(f"Created blank annotation template: {output.resolve()}")
    print("Allowed movement_label values: correct, incorrect, uncertain")

if __name__ == "__main__":
    main()
