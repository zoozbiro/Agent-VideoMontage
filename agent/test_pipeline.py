#!/usr/bin/env python3

import argparse
import json
import subprocess
from pathlib import Path

DEFAULT_SOURCE = Path("/mnt/video/01_RUSHS/X5/2026-09-13/VID_20260911_103908_00_001.insv")
DEFAULT_WORK = Path("/mnt/video/02_WORK/test-project")
DEFAULT_EXPORT = Path("/mnt/video/03_EXPORT/test-project")


def run(cmd: list[str]) -> None:
    print("$", " ".join(cmd))
    subprocess.run(cmd, check=True)


def probe(source: Path) -> dict:
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration:stream=index,codec_type,codec_name,width,height",
        "-of", "json", str(source),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return json.loads(result.stdout)


def main() -> None:
    parser = argparse.ArgumentParser(description="Single-video prototype pipeline")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--work", type=Path, default=DEFAULT_WORK)
    parser.add_argument("--export", type=Path, default=DEFAULT_EXPORT)
    parser.add_argument("--test-duration", type=float, default=30.0)
    parser.add_argument("--final-duration", type=float, default=15.0)
    args = parser.parse_args()

    if not args.source.exists():
        raise SystemExit(f"Source introuvable: {args.source}")
    if args.final_duration > args.test_duration:
        raise SystemExit("final-duration doit être <= test-duration")

    args.work.mkdir(parents=True, exist_ok=True)
    args.export.mkdir(parents=True, exist_ok=True)

    metadata = probe(args.source)
    (args.work / "source.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    sample = args.work / "source-test.mp4"
    run([
        "ffmpeg", "-hide_banner", "-y",
        "-ss", "0", "-t", str(args.test_duration),
        "-i", str(args.source),
        "-map", "0:0",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "26",
        "-an", "-movflags", "+faststart",
        str(sample),
    ])

    final = args.export / "prototype-reel.mp4"
    run([
        "ffmpeg", "-hide_banner", "-y",
        "-ss", "0", "-t", str(args.final_duration),
        "-i", str(sample),
        "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "24",
        "-an", "-movflags", "+faststart",
        str(final),
    ])

    print()
    print("Prototype terminée")
    print(f"Source      : {args.source}")
    print(f"Échantillon : {sample}")
    print(f"Export      : {final}")
    print("Note: ce prototype mappe volontairement le premier flux vidéo. Le vrai reframing 360 sera ajouté après validation du pipeline.")


if __name__ == "__main__":
    main()
