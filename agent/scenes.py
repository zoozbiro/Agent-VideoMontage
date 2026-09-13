#!/usr/bin/env python3
"""Detect candidate scene changes with lightweight frame differences."""
import argparse
import json
import subprocess
from pathlib import Path

DEFAULT_OUTPUT = Path("/mnt/video/02_WORK/scenes.json")
DEFAULT_FPS = 2.0
DEFAULT_WIDTH = 160
DEFAULT_HEIGHT = 90
DEFAULT_THRESHOLD = 12.0
DEFAULT_MIN_GAP = 2.0


def detect_scenes(source: Path, threshold: float, fps: float, width: int, height: int, min_gap: float) -> list[dict]:
    frame_size = width * height
    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(source),
        "-vf", f"fps={fps},scale={width}:{height},format=gray",
        "-an", "-f", "rawvideo", "-pix_fmt", "gray", "-",
    ]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    scenes = []
    previous = None
    frame_index = 0
    last_scene_time = -min_gap
    try:
        while True:
            data = process.stdout.read(frame_size)
            if len(data) < frame_size:
                break
            if previous is not None:
                difference = sum(abs(a - b) for a, b in zip(data, previous)) / frame_size
                timestamp = frame_index / fps
                if difference >= threshold and timestamp - last_scene_time >= min_gap:
                    scenes.append({"time": round(timestamp, 3), "score": round(difference, 3)})
                    last_scene_time = timestamp
            previous = data
            frame_index += 1
    finally:
        stderr = process.stderr.read().decode("utf-8", errors="replace")
        returncode = process.wait()
    if returncode != 0:
        raise RuntimeError(f"ffmpeg failed with exit {returncode}: {stderr.strip()}")
    return scenes


def main() -> None:
    parser = argparse.ArgumentParser(description="Detect candidate scene changes in a video proxy")
    parser.add_argument("source", type=Path)
    parser.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD,
                        help="Mean grayscale pixel difference (0-255)")
    parser.add_argument("--fps", type=float, default=DEFAULT_FPS, help="Frames sampled per second")
    parser.add_argument("--width", type=int, default=DEFAULT_WIDTH)
    parser.add_argument("--height", type=int, default=DEFAULT_HEIGHT)
    parser.add_argument("--min-gap", type=float, default=DEFAULT_MIN_GAP,
                        help="Minimum seconds between candidates")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    if args.fps <= 0 or args.width <= 0 or args.height <= 0:
        raise SystemExit("fps, width and height must be positive")
    if args.threshold < 0 or args.min_gap < 0:
        raise SystemExit("threshold and min-gap must be non-negative")
    scenes = detect_scenes(args.source, args.threshold, args.fps, args.width, args.height, args.min_gap)
    payload = {
        "source": str(args.source), "method": "frame_difference", "fps": args.fps,
        "sample_size": [args.width, args.height], "threshold": args.threshold,
        "min_gap": args.min_gap, "scene_changes": scenes, "count": len(scenes),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Scènes candidates : {len(scenes)}")
    print("Méthode           : frame_difference")
    print(f"Seuil             : {args.threshold}")
    print(f"Échantillonnage   : {args.fps:g} fps, {args.width}x{args.height}")
    print(f"Résultat          : {args.output}")
    for scene in scenes[:30]:
        print(f"  {scene['time']:8.3f}s  score={scene['score']:6.2f}")


if __name__ == "__main__":
    main()
