#!/usr/bin/env python3

import argparse
import json
import subprocess
from pathlib import Path

DEFAULT_INVENTORY = Path("/mnt/video/02_WORK/inventory.json")
DEFAULT_OUTPUT_ROOT = Path("/mnt/video/02_WORK/proxies")


def load_inventory(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def make_proxy(source: Path, output: Path, force: bool = False) -> str:
    if output.exists() and not force:
        return "skipped"

    output.parent.mkdir(parents=True, exist_ok=True)
    temp = output.with_suffix(output.suffix + ".part")
    if temp.exists():
        temp.unlink()

    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-y",
        "-i",
        str(source),
        "-map",
        "0:0",
        "-vf",
        "scale=-2:720",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "28",
        "-an",
        "-movflags",
        "+faststart",
        str(temp),
    ]

    try:
        subprocess.run(cmd, check=True)
        temp.replace(output)
        return "created"
    except Exception:
        if temp.exists():
            temp.unlink()
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate lightweight H.264 proxies from INSV inventory")
    parser.add_argument("--inventory", type=Path, default=DEFAULT_INVENTORY)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--limit", type=int, default=0, help="Process at most N eligible files (0 = all)")
    parser.add_argument("--force", action="store_true", help="Regenerate existing proxies")
    args = parser.parse_args()

    data = load_inventory(args.inventory)
    entries = [item for item in data.get("files", []) if item.get("status") == "new"]
    if args.limit > 0:
        entries = entries[:args.limit]

    created = skipped = errors = 0

    for index, item in enumerate(entries, start=1):
        source = Path(item["file"])
        relative = Path(item["relative_path"])
        output = args.output_root / relative.with_suffix(".mp4")
        print(f"[{index}/{len(entries)}] {source.name}")
        print(f"  -> {output}")
        try:
            status = make_proxy(source, output, force=args.force)
            if status == "created":
                created += 1
                print("  OK")
            else:
                skipped += 1
                print("  SKIP (already exists)")
        except subprocess.CalledProcessError as exc:
            errors += 1
            print(f"  ERROR (ffmpeg exit {exc.returncode})")
        except Exception as exc:
            errors += 1
            print(f"  ERROR: {exc}")

    print()
    print(f"Créés   : {created}")
    print(f"Ignorés : {skipped}")
    print(f"Erreurs : {errors}")


if __name__ == "__main__":
    main()
