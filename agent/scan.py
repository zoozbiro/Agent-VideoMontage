#!/usr/bin/env python3
"""Select a camera/date folder and build a media inventory."""
import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

RUSH_DIR = Path("/mnt/video/01_RUSHS")
WORK_DIR = Path("/mnt/video/02_WORK")
OUTPUT_FILE = WORK_DIR / "inventory.json"
MIN_DURATION = 3.0
MEDIA_EXTENSIONS = {".insv", ".mp4", ".mov", ".m4v", ".avi", ".mkv"}


def probe(file: Path) -> dict:
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration,size",
        "-of", "json", str(file),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    data = json.loads(result.stdout)
    fmt = data.get("format", {})
    return {
        "duration": float(fmt.get("duration", 0)),
        "size": int(fmt.get("size", file.stat().st_size)),
    }


def choose_directory(prompt: str, directories: list[Path]) -> Path:
    if not directories:
        raise SystemExit("Aucun dossier disponible.")
    print()
    print(prompt)
    for index, directory in enumerate(directories, start=1):
        print(f"  {index}. {directory.name}")
    while True:
        choice = input("Choix : ").strip()
        try:
            index = int(choice)
            if 1 <= index <= len(directories):
                return directories[index - 1]
        except ValueError:
            pass
        print(f"Choisis un numéro entre 1 et {len(directories)}.")


def select_source() -> Path:
    cameras = sorted(
        path for path in RUSH_DIR.iterdir()
        if path.is_dir() and not path.name.startswith("@")
    )
    camera_dir = choose_directory("Sur quel dossier caméra veux-tu travailler ?", cameras)

    dates = sorted(
        path for path in camera_dir.iterdir()
        if path.is_dir() and not path.name.startswith("@")
    )
    if not dates:
        raise SystemExit(f"Aucun sous-dossier date trouvé dans {camera_dir}.")
    date_dir = choose_directory(f"Quelle date veux-tu traiter dans {camera_dir.name} ?", dates)
    return date_dir


def main() -> None:
    parser = argparse.ArgumentParser(description="Select and inventory one camera/date folder")
    parser.add_argument("--source", type=Path, help="Skip interactive selection and scan this folder")
    args = parser.parse_args()

    WORK_DIR.mkdir(parents=True, exist_ok=True)
    source_dir = args.source if args.source else select_source()
    if not source_dir.is_dir():
        raise SystemExit(f"Dossier source introuvable : {source_dir}")

    files = sorted(
        path for path in source_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in MEDIA_EXTENSIONS and "@eaDir" not in path.parts
    )
    inventory = []

    print()
    print(f"Source sélectionnée : {source_dir}")
    print()
    for file in files:
        try:
            info = probe(file)
            status = "new" if info["duration"] >= MIN_DURATION else "too_short"
            inventory.append({
                "file": str(file),
                "relative_path": str(file.relative_to(source_dir)),
                "filename": file.name,
                "duration": round(info["duration"], 3),
                "size": info["size"],
                "status": status,
            })
            print(f"[{status:10}] {info['duration']:8.1f}s {file.name}")
        except Exception as exc:
            inventory.append({
                "file": str(file),
                "relative_path": str(file.relative_to(source_dir)),
                "filename": file.name,
                "status": "error",
                "error": str(exc),
            })
            print(f"[ERROR] {file.name}: {exc}")

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": str(source_dir),
        "camera": source_dir.parent.name,
        "date": source_dir.name,
        "total_files": len(inventory),
        "files": inventory,
    }
    OUTPUT_FILE.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")

    print()
    print(f"Médias trouvés : {len(files)}")
    print(f"Inventaire     : {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
