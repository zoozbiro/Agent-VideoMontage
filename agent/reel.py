#!/usr/bin/env python3
"""Build an automatic vertical Reel from the selected camera/date inventory."""
import argparse
import json
import subprocess
from pathlib import Path

DEFAULT_INVENTORY = Path("/mnt/video/02_WORK/inventory.json")
DEFAULT_WORK = Path("/mnt/video/02_WORK/reel")
DEFAULT_EXPORT_ROOT = Path("/mnt/video/03_EXPORT")
DEFAULT_DURATION = 30.0
CLIP_DURATION = 4.0


def run(cmd: list[str]) -> None:
    print("$", " ".join(cmd))
    subprocess.run(cmd, check=True)


def probe(path: Path) -> dict:
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration:stream=index,codec_type,width,height",
        "-of", "json", str(path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    data = json.loads(result.stdout)
    video = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), {})
    return {
        "duration": float(data.get("format", {}).get("duration", 0) or 0),
        "width": int(video.get("width", 0) or 0),
        "height": int(video.get("height", 0) or 0),
    }


def vertical_filter(width: int, height: int) -> str:
    if width > height * 1.15:
        # Landscape camera: fill the Reel and crop the sides.
        return "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"
    if abs(width - height) <= max(width, height) * 0.08:
        # X5 fallback: keep the square image and place it in a vertical canvas.
        return "scale=1080:1080,pad=1080:1920:0:420"
    # Already vertical or close to it.
    return "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2"


def candidate_starts(duration: float, clip_duration: float) -> list[float]:
    usable = max(0.0, duration - clip_duration)
    if usable <= 0:
        return [0.0]
    # Spread candidates through the whole source instead of taking its first seconds.
    ratios = (0.10, 0.30, 0.50, 0.70, 0.90)
    return [round(usable * ratio, 3) for ratio in ratios]


def main() -> None:
    parser = argparse.ArgumentParser(description="Automatically assemble a vertical Reel")
    parser.add_argument("--inventory", type=Path, default=DEFAULT_INVENTORY)
    parser.add_argument("--work", type=Path, default=DEFAULT_WORK)
    parser.add_argument("--export-root", type=Path, default=DEFAULT_EXPORT_ROOT)
    parser.add_argument("--duration", type=float, default=DEFAULT_DURATION)
    parser.add_argument("--clip-duration", type=float, default=CLIP_DURATION)
    parser.add_argument("--max-clips", type=int, default=0, help="Maximum clips (0 = calculated from duration)")
    args = parser.parse_args()

    data = json.loads(args.inventory.read_text(encoding="utf-8"))
    entries = [item for item in data.get("files", []) if item.get("status") == "new"]
    if not entries:
        raise SystemExit("Aucune vidéo exploitable dans l'inventaire.")
    if args.duration <= 0 or args.clip_duration <= 0:
        raise SystemExit("duration et clip-duration doivent être positifs.")

    camera = data.get("camera", "camera")
    date = data.get("date", "date")
    work_dir = args.work / camera / date
    clips_dir = work_dir / "clips"
    work_dir.mkdir(parents=True, exist_ok=True)
    clips_dir.mkdir(parents=True, exist_ok=True)

    target_clips = args.max_clips or max(1, round(args.duration / args.clip_duration))
    # Build a round-robin candidate list so one long file cannot monopolize the Reel.
    candidates: list[dict] = []
    for item in entries:
        source = Path(item["file"])
        try:
            meta = probe(source)
        except Exception as exc:
            print(f"[WARN] Impossible d'analyser {source.name}: {exc}")
            continue
        for start in candidate_starts(meta["duration"], args.clip_duration):
            candidates.append({
                "source": source,
                "start": start,
                "duration": min(args.clip_duration, max(0.1, meta["duration"] - start)),
                "width": meta["width"],
                "height": meta["height"],
                "filename": source.name,
            })

    if not candidates:
        raise SystemExit("Aucun segment candidat disponible.")

    # Round-robin by source: first pass takes one candidate from each file,
    # then repeats until the target duration is reached.
    grouped: dict[str, list[dict]] = {}
    for candidate in candidates:
        grouped.setdefault(str(candidate["source"]), []).append(candidate)
    groups = list(grouped.values())
    selected: list[dict] = []
    round_index = 0
    while len(selected) < target_clips:
        added = False
        for group in groups:
            if round_index < len(group) and len(selected) < target_clips:
                selected.append(group[round_index])
                added = True
        if not added:
            break
        round_index += 1

    if not selected:
        raise SystemExit("Impossible de sélectionner des segments.")

    rendered: list[Path] = []
    manifest = []
    for index, candidate in enumerate(selected, start=1):
        output = clips_dir / f"clip-{index:03d}.mp4"
        duration = candidate["duration"]
        vf = vertical_filter(candidate["width"], candidate["height"])
        run([
            "ffmpeg", "-hide_banner", "-y",
            "-ss", str(candidate["start"]),
            "-t", str(duration),
            "-i", str(candidate["source"]),
            "-map", "0:v:0",
            "-vf", vf,
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
            "-an", "-movflags", "+faststart",
            str(output),
        ])
        rendered.append(output)
        manifest.append({
            "output": str(output),
            "source": str(candidate["source"]),
            "start": candidate["start"],
            "duration": round(duration, 3),
        })

    concat_file = work_dir / "concat.txt"
    concat_file.write_text("\n".join(f"file '{path}'" for path in rendered) + "\n", encoding="utf-8")
    export_dir = args.export_root / camera / date
    export_dir.mkdir(parents=True, exist_ok=True)
    final = export_dir / "reel-001.mp4"
    run([
        "ffmpeg", "-hide_banner", "-y",
        "-f", "concat", "-safe", "0", "-i", str(concat_file),
        "-c", "copy", "-movflags", "+faststart",
        str(final),
    ])

    manifest_path = work_dir / "manifest.json"
    manifest_path.write_text(json.dumps({
        "camera": camera,
        "date": date,
        "target_duration": args.duration,
        "clip_duration": args.clip_duration,
        "selected_clips": manifest,
        "output": str(final),
        "mode": "automatic_v1",
        "note": "Heuristic montage: distributed segments, vertical crop/pad. X5 is not yet true 360 reframed.",
    }, indent=2, ensure_ascii=False), encoding="utf-8")

    print()
    print("REEL AUTOMATIQUE TERMINÉ")
    print(f"Caméra     : {camera}")
    print(f"Date       : {date}")
    print(f"Clips      : {len(rendered)}")
    print(f"Durée cible: {args.duration:.1f}s")
    print(f"Export     : {final}")
    print(f"Manifeste  : {manifest_path}")
    print("Note       : v1 automatique sans IA de sélection ni reframing 360 X5.")


if __name__ == "__main__":
    main()
