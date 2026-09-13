#!/usr/bin/env python3
"""Inspect the two video streams inside an Insta360 X5 INSV file.

This intentionally does NOT attempt to stitch the lenses. It creates short,
low-resolution samples from each video stream so we can verify the source
layout before selecting a real stitching backend.
"""
import argparse
import json
import subprocess
from pathlib import Path


def ffprobe_streams(source: Path) -> list[dict]:
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "v",
        "-show_entries",
        "stream=index,codec_name,width,height,r_frame_rate,duration,bit_rate,side_data_list",
        "-of", "json", str(source),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return json.loads(result.stdout).get("streams", [])


def make_sample(source: Path, stream_index: int, output: Path, duration: float) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-hide_banner", "-y",
        "-ss", "0", "-t", str(duration),
        "-i", str(source),
        "-map", f"0:{stream_index}",
        "-vf", "scale=640:640",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "30",
        "-an", "-movflags", "+faststart", str(output),
    ]
    subprocess.run(cmd, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect Insta360 X5 INSV video streams")
    parser.add_argument("source", type=Path)
    parser.add_argument("--duration", type=float, default=5.0)
    parser.add_argument("--output-dir", type=Path, default=Path("/mnt/video/02_WORK/test-project/360-inspect"))
    args = parser.parse_args()

    streams = ffprobe_streams(args.source)
    print(f"Video streams: {len(streams)}")
    for stream in streams:
        print(json.dumps(stream, ensure_ascii=False))

    if len(streams) < 2:
        raise SystemExit("Expected at least two video streams in the X5 INSV file")

    samples = []
    for position, stream in enumerate(streams[:2]):
        index = int(stream["index"])
        output = args.output_dir / f"lens-{position + 1}-stream-{index}.mp4"
        print(f"Creating sample: {output}")
        make_sample(args.source, index, output, args.duration)
        samples.append(str(output))

    manifest = {
        "source": str(args.source),
        "duration": args.duration,
        "streams": streams[:2],
        "samples": samples,
        "next_step": "Select and validate a real X5 stitching backend before implementing 360 reframing.",
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = args.output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Manifest: {manifest_path}")


if __name__ == "__main__":
    main()
