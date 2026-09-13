#!/usr/bin/env python3
"""Detect likely scene changes in a generated video proxy.

This first implementation uses FFmpeg's scene score filter. It is intentionally
lightweight: no ML model is required, and the result is a candidate list for the
montage brain rather than a final editing decision.
"""
import argparse
import json
import subprocess
from pathlib import Path

DEFAULT_OUTPUT = Path("/mnt/video/02_WORK/scenes.json")
DEFAULT_THRESHOLD = 0.18


def detect_scenes(source: Path, threshold: float) -> list[dict]:
    filter_expr = f"select='gt(scene,{threshold})',showinfo"
    cmd = [
        "ffmpeg", "-hide_banner", "-i", str(source),
        "-vf", filter_expr,
        "-an", "-f", "null", "-",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    scenes = []
    for line in result.stderr.splitlines():
        if "pts_time:" not in line or "Parsed_showinfo" not in line:
            continue
        try:
            parts = dict(
                part.split(":", 1)
                for part in line.split()
                if ":" in part
            )
            timestamp = float(parts["pts_time"])
            scenes.append({"time": round(timestamp, 3)})
        except (KeyError, ValueError):
            continue
    return scenes


def main() -> None:
    parser = argparse.ArgumentParser(description="Detect candidate scene changes in a video proxy")
    parser.add_argument("source", type=Path)
    parser.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    scenes = detect_scenes(args.source, args.threshold)
    payload = {
        "source": str(args.source),
        "threshold": args.threshold,
        "scene_changes": scenes,
        "count": len(scenes),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Scènes candidates : {len(scenes)}")
    print(f"Seuil             : {args.threshold}")
    print(f"Résultat          : {args.output}")
    for scene in scenes[:30]:
        print(f"  {scene['time']:8.3f}s")


if __name__ == "__main__":
    main()
