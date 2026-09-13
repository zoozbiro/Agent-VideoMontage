#!/usr/bin/env python3
"""Create a contact sheet from candidate scene timestamps."""
import argparse
import json
import subprocess
from pathlib import Path

DEFAULT_SCENES = Path("/mnt/video/02_WORK/scenes.json")
DEFAULT_OUTPUT = Path("/mnt/video/02_WORK/scene-contact-sheet.jpg")
DEFAULT_WORK = Path("/mnt/video/02_WORK/scene-frames")


def make_frame(source: Path, timestamp: float, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-ss", str(timestamp), "-i", str(source),
        "-frames:v", "1", "-vf", "scale=320:180",
        "-q:v", "3", str(output),
    ]
    subprocess.run(cmd, check=True)


def make_sheet(frames: list[Path], output: Path, columns: int) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    inputs = []
    for frame in frames:
        inputs.extend(["-i", str(frame)])
    layout = f"tile={columns}x"
    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        *inputs,
        "-filter_complex", layout,
        "-frames:v", "1", "-q:v", "3", str(output),
    ]
    subprocess.run(cmd, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a contact sheet from scene candidates")
    parser.add_argument("source", type=Path)
    parser.add_argument("--scenes", type=Path, default=DEFAULT_SCENES)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--work-dir", type=Path, default=DEFAULT_WORK)
    parser.add_argument("--columns", type=int, default=5)
    args = parser.parse_args()

    if args.columns <= 0:
        raise SystemExit("columns must be positive")

    data = json.loads(args.scenes.read_text(encoding="utf-8"))
    candidates = data.get("scene_changes", [])
    if not candidates:
        raise SystemExit("No scene candidates found")

    frames = []
    for index, scene in enumerate(candidates, start=1):
        timestamp = float(scene["time"])
        frame = args.work_dir / f"scene-{index:03d}-{timestamp:.3f}.jpg"
        print(f"[{index}/{len(candidates)}] {timestamp:.3f}s")
        make_frame(args.source, timestamp, frame)
        frames.append(frame)

    make_sheet(frames, args.output, args.columns)
    print(f"\nPlanche : {args.output}")
    print(f"Images  : {len(frames)}")


if __name__ == "__main__":
    main()
