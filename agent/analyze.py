#!/usr/bin/env python3
"""Create lightweight technical analysis for generated video proxies."""
import argparse
import json
import subprocess
from pathlib import Path

DEFAULT_PROXY_ROOT = Path("/mnt/video/02_WORK/proxies")
DEFAULT_OUTPUT = Path("/mnt/video/02_WORK/analysis.json")


def probe(path: Path) -> dict:
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries",
        "format=duration,size:stream=index,codec_type,codec_name,width,height,r_frame_rate,bit_rate",
        "-of", "json", str(path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    data = json.loads(result.stdout)
    fmt = data.get("format", {})
    streams = data.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), {})
    return {
        "duration": round(float(fmt.get("duration", 0)), 3),
        "size": int(fmt.get("size", path.stat().st_size)),
        "video": {
            "codec": video.get("codec_name"),
            "width": video.get("width"),
            "height": video.get("height"),
            "fps": video.get("r_frame_rate"),
            "bit_rate": video.get("bit_rate"),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze proxy videos")
    parser.add_argument("--proxy-root", type=Path, default=DEFAULT_PROXY_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--limit", type=int, default=0, help="Analyze at most N files (0 = all)")
    args = parser.parse_args()

    files = sorted(args.proxy_root.rglob("*.mp4"))
    if args.limit > 0:
        files = files[:args.limit]

    entries = []
    for index, path in enumerate(files, start=1):
        print(f"[{index}/{len(files)}] {path.name}")
        try:
            info = probe(path)
            entries.append({"file": str(path), "relative_path": str(path.relative_to(args.proxy_root)), "status": "ok", **info})
        except Exception as exc:
            entries.append({"file": str(path), "relative_path": str(path.relative_to(args.proxy_root)), "status": "error", "error": str(exc)})
            print(f"  ERROR: {exc}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"source": str(args.proxy_root), "total_files": len(files), "files": entries}, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nAnalyse : {args.output}")
    print(f"Fichiers : {len(files)}")


if __name__ == "__main__":
    main()
