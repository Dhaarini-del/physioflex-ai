from pathlib import Path
import argparse
import csv
import cv2

try:
    import mediapipe as mp
except ImportError as exc:
    raise SystemExit("MediaPipe is not installed. Run: pip install -r requirements.txt") from exc

VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".webm", ".mpeg", ".mpg"}

def main():
    parser = argparse.ArgumentParser(description="Extract MediaPipe Pose landmarks from videos.")
    parser.add_argument("--input", default="data/raw")
    parser.add_argument("--output", default="data/pose")
    parser.add_argument("--sample-every", type=int, default=1,
                        help="Process every Nth frame. Default: 1 (all frames).")
    parser.add_argument("--min-detection-confidence", type=float, default=0.5)
    parser.add_argument("--min-tracking-confidence", type=float, default=0.5)
    args = parser.parse_args()

    src, out = Path(args.input), Path(args.output)
    if not src.exists():
        raise SystemExit(f"Input folder does not exist: {src.resolve()}")
    if args.sample_every < 1:
        raise SystemExit("--sample-every must be at least 1.")
    out.mkdir(parents=True, exist_ok=True)

    videos = [p for p in src.rglob("*") if p.is_file() and p.suffix.lower() in VIDEO_EXTENSIONS]
    if not videos:
        print(f"No supported videos found under {src.resolve()}")
        return

    mp_pose = mp.solutions.pose
    for video in videos:
        # Preserve relative subfolders and avoid collisions between equal filenames.
        rel = video.relative_to(src)
        target_dir = out / rel.parent
        target_dir.mkdir(parents=True, exist_ok=True)
        output_csv = target_dir / f"{video.stem}_pose.csv"

        cap = cv2.VideoCapture(str(video))
        if not cap.isOpened():
            print(f"SKIP: cannot open {video}")
            continue

        fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
        headers = ["video_id", "frame", "timestamp_ms", "fps"]
        for i in range(33):
            headers += [f"x{i}", f"y{i}", f"z{i}", f"visibility{i}"]

        written = 0
        frame_no = 0
        try:
            with mp_pose.Pose(
                static_image_mode=False,
                model_complexity=1,
                min_detection_confidence=args.min_detection_confidence,
                min_tracking_confidence=args.min_tracking_confidence
            ) as pose, output_csv.open("w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(headers)
                while True:
                    ok, frame = cap.read()
                    if not ok:
                        break
                    if frame_no % args.sample_every == 0:
                        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        result = pose.process(rgb)
                        if result.pose_landmarks:
                            row = [video.stem, frame_no,
                                   round(cap.get(cv2.CAP_PROP_POS_MSEC), 3), fps]
                            for point in result.pose_landmarks.landmark:
                                row.extend([point.x, point.y, point.z, point.visibility])
                            writer.writerow(row)
                            written += 1
                    frame_no += 1
        finally:
            cap.release()

        print(f"{video.name}: {written} pose frames -> {output_csv}")

if __name__ == "__main__":
    main()
