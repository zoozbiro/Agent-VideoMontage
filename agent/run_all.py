#!/usr/bin/env python3
"""Run the current video-agent pipeline end-to-end for one selected folder."""
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
AGENT_DIR = REPO_ROOT / "agent"
INVENTORY = Path("/mnt/video/02_WORK/inventory.json")
PROXY_ROOT = Path("/mnt/video/02_WORK/proxies")


def run_step(name: str, command: list[str]) -> None:
    print("\n" + "=" * 72)
    print(name)
    print("=" * 72)
    print("$", " ".join(command))
    subprocess.run(command, cwd=REPO_ROOT, check=True)


def is_media_file(path: Path) -> bool:
    """Return True for real proxy files, excluding Synology metadata trees."""
    return path.is_file() and "@eaDir" not in path.parts


def load_inventory() -> dict:
    if not INVENTORY.exists():
        raise SystemExit(f"Inventaire introuvable : {INVENTORY}")
    return json.loads(INVENTORY.read_text(encoding="utf-8"))


def main() -> int:
    python = sys.executable

    # scan.py asks the user which camera folder and date folder to process.
    run_step("1/5 — Sélection et inventaire des rushs", [python, str(AGENT_DIR / "scan.py")])
    inventory = load_inventory()
    source_dir = Path(inventory["source"])
    entries = [item for item in inventory.get("files", []) if item.get("status") == "new"]

    if not entries:
        print("\nAucune vidéo exploitable dans le dossier sélectionné.")
        return 1

    # proxy.py consumes the inventory produced by scan.py, so it processes only
    # the selected camera/date folder rather than the whole NAS library.
    run_step("2/5 — Génération des proxies", [python, str(AGENT_DIR / "proxy.py")])

    selected_proxies = []
    for item in entries:
        relative = Path(item["relative_path"])
        proxy = PROXY_ROOT / relative.with_suffix(".mp4")
        if is_media_file(proxy):
            selected_proxies.append(proxy)

    if not selected_proxies:
        print("\nAucun proxy trouvé pour le dossier sélectionné.")
        return 1

    # Analyze only the proxies belonging to the selected camera/date.
    run_step(
        "3/5 — Analyse technique des proxies",
        [python, str(AGENT_DIR / "analyze.py"), "--proxy-root", str(PROXY_ROOT / source_dir.name)],
    )

    scenes_dir = Path("/mnt/video/02_WORK/scenes") / inventory.get("camera", source_dir.parent.name) / inventory.get("date", source_dir.name)
    for index, proxy in enumerate(selected_proxies, start=1):
        output = scenes_dir / proxy.relative_to(PROXY_ROOT).with_suffix(".json")
        run_step(
            f"4/5 — Détection des scènes [{index}/{len(selected_proxies)}]",
            [python, str(AGENT_DIR / "scenes.py"), str(proxy), "--output", str(output)],
        )

    # The current Reel prototype is intentionally single-source. Use the first
    # valid clip from the selected folder until the future highlight selector
    # can assemble multiple clips automatically.
    first_source = Path(entries[0]["file"])
    run_step(
        "5/5 — Prototype Reel vertical",
        [python, str(AGENT_DIR / "test_pipeline.py"), "--source", str(first_source)],
    )

    print("\n" + "=" * 72)
    print("PIPELINE TERMINÉ")
    print("=" * 72)
    print(f"Dossier sélectionné : {source_dir}")
    print(f"Vidéos traitées     : {len(selected_proxies)}")
    print(f"Proxies             : {PROXY_ROOT}")
    print(f"Scènes              : {scenes_dir}")
    print("Prototype            : /mnt/video/03_EXPORT/test-project/prototype-reel.mp4")
    print("\nNote : le pipeline actuel ne fait pas encore le stitching 360 X5 ni le reframing 360 automatique.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as exc:
        print(f"\nERREUR : étape interrompue (code {exc.returncode}).", file=sys.stderr)
        raise SystemExit(exc.returncode)
