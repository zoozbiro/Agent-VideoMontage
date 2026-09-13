#!/usr/bin/env python3

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

RUSH_DIR = Path("/mnt/video/01_RUSHS")
WORK_DIR = Path("/mnt/video/02_WORK")
OUTPUT_FILE = WORK_DIR / "inventory.json"

MIN_DURATION = 3.0


def probe(file: Path) -> dict:
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration,size",
        "-of", "json",
        str(file),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    data = json.loads(result.stdout)
    fmt = data.get("format", {})

    return {
        "duration": float(fmt.get("duration", 0)),
        "size": int(fmt.get("size", file.stat().st_size)),
    }


def main():
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    files = sorted(RUSH_DIR.rglob("*.insv"))
    inventory = []

    for file in files:
        try:
            info = probe(file)
            status = "new" if info["duration"] >= MIN_DURATION else "too_short"

            inventory.append({
                "file": str(file),
                "relative_path": str(file.relative_to(RUSH_DIR)),
                "filename": file.name,
                "duration": round(info["duration"], 3),
                "size": info["size"],
                "status": status,
            })

            print(f"[{status:10}] {info['duration']:8.1f}s {file.name}")

        except Exception as exc:
            inventory.append({
                "file": str(file),
                "relative_path": str(file.relative_to(RUSH_DIR)),
                "filename": file.name,
                "status": "error",
                "error": str(exc),
            })
            print(f"[ERROR] {file.name}: {exc}")

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": str(RUSH_DIR),
        "total_files": len(inventory),
        "files": inventory,
    }

    OUTPUT_FILE.write_text(
        json.dumps(output, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print()
    print(f"INSV trouvés : {len(files)}")
    print(f"Inventaire   : {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
