from pathlib import Path
import argparse
import numpy as np
import pandas as pd

def angle(a, b, c):
    """2D projected angle ABC in degrees; returns NaN for invalid/zero-length vectors."""
    ba = np.asarray(a, dtype=float) - np.asarray(b, dtype=float)
    bc = np.asarray(c, dtype=float) - np.asarray(b, dtype=float)
    denom = np.linalg.norm(ba) * np.linalg.norm(bc)
    if not np.isfinite(denom) or denom == 0:
        return np.nan
    cosine = np.clip(np.dot(ba, bc) / denom, -1.0, 1.0)
    return float(np.degrees(np.arccos(cosine)))

def landmark(df, idx):
    return np.column_stack([df[f"x{idx}"], df[f"y{idx}"]])

def process_file(path):
    df = pd.read_csv(path)
    required = {"video_id", "frame", "timestamp_ms"}
    if not required.issubset(df.columns):
        print(f"SKIP missing required columns: {path}")
        return None

    # MediaPipe Pose landmark indices:
    # left shoulder 11, elbow 13, wrist 15, hip 23, knee 25, ankle 27
    # right shoulder 12, elbow 14, wrist 16, hip 24, knee 26, ankle 28
    triples = {
        "left_knee_angle": (23, 25, 27),
        "right_knee_angle": (24, 26, 28),
        "left_elbow_angle": (11, 13, 15),
        "right_elbow_angle": (12, 14, 16),
        "left_shoulder_angle": (13, 11, 23),
        "right_shoulder_angle": (14, 12, 24),
    }

    result = pd.DataFrame({
        "video_id": df["video_id"].astype(str),
        "frame": df["frame"],
        "timestamp_ms": df["timestamp_ms"],
    })

    for name, (a, b, c) in triples.items():
        pa, pb, pc = landmark(df, a), landmark(df, b), landmark(df, c)
        result[name] = [
            angle(x, y, z) for x, y, z in zip(pa, pb, pc)
        ]

    # Minimum visibility across the landmarks used for each angle.
    for name, triple in triples.items():
        vis_cols = [f"visibility{i}" for i in triple]
        if all(col in df.columns for col in vis_cols):
            result[name + "_visibility"] = df[vis_cols].min(axis=1)

    result["knee_asymmetry_deg"] = (
        result["left_knee_angle"] - result["right_knee_angle"]
    ).abs()
    return result

def main():
    parser = argparse.ArgumentParser(description="Convert pose CSVs to movement features.")
    parser.add_argument("--input", default="data/pose")
    parser.add_argument("--output", default="data/features/movement_features.csv")
    args = parser.parse_args()

    src, output = Path(args.input), Path(args.output)
    if not src.exists():
        raise SystemExit(f"Pose folder does not exist: {src.resolve()}")

    files = list(src.rglob("*_pose.csv"))
    if not files:
        raise SystemExit(f"No *_pose.csv files found under {src.resolve()}")

    frames = []
    for path in files:
        frame_features = process_file(path)
        if frame_features is not None and not frame_features.empty:
            frames.append(frame_features)

    if not frames:
        raise SystemExit("No valid pose feature rows were produced.")

    all_frames = pd.concat(frames, ignore_index=True)
    output.parent.mkdir(parents=True, exist_ok=True)
    all_frames.to_csv(output, index=False)

    angle_cols = [c for c in all_frames.columns if c.endswith("_angle")]
    summary = all_frames.groupby("video_id")[angle_cols].agg(["mean", "std", "min", "max"])
    summary.columns = ["_".join(col) for col in summary.columns]
    summary = summary.reset_index()
    summary_path = output.with_name(output.stem + "_video_summary.csv")
    summary.to_csv(summary_path, index=False)

    print(f"Frame features: {output.resolve()}")
    print(f"Video summary: {summary_path.resolve()}")
    print(f"Videos: {summary['video_id'].nunique()}, frames: {len(all_frames)}")

if __name__ == "__main__":
    main()
