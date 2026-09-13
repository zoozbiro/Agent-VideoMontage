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
DEFAULT_THRESHOLD = 0.35


def detect_scenes(source: Path, threshold: float) -> list[dict]:
    filter_expr = f"select='gt(scene,{threshold})',metadata=print:file=-"
    cmd = [
        "ffmpeg", "-hide_banner", "-i", str(source),
        "-vf", filter_expr,
        "-an", "-f", "null", "-",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    scenes = []
    for line in result.stderr.splitlines():
        if "lavfi.scene_score=" not in line:
            continue
        try:
            timestamp = None
            score = None
            for part in line.split():
                if part.startswith("pts_time:"):
                    timestamp = float(part.split(":", 1)[1])
                elif part.startswith("lavfi.scene_score="):
                    score = float(part.split("=", 1)[1])
            if timestamp is not None and score is not None:
                scenes.append({"time": round(timestamp, 3), "score": round(score, 4)})
        except ValueError:
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
    print(f"Résultat          : {args.output}")
    for scene in scenes[:20]:
        print(f"  {scene['time']:8.3f}s  score={scene['score']:.4f}")


if __name__ == "__main__":
    main()
