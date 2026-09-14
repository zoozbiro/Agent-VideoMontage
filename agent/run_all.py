#!/usr/bin/env python3
"""Run the current video-agent pipeline end-to-end."""
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
AGENT_DIR = REPO_ROOT / "agent"
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


def main() -> int:
    python = sys.executable
    source = Path("/mnt/video/01_RUSHS")

    steps = [
        ("1/5 — Inventaire des rushs", [python, str(AGENT_DIR / "scan.py")]),
        ("2/5 — Génération des proxies", [python, str(AGENT_DIR / "proxy.py")]),
        ("3/5 — Analyse technique des proxies", [python, str(AGENT_DIR / "analyze.py")]),
    ]

    for name, command in steps:
        run_step(name, command)

    # Scene detection is intentionally run on every generated proxy. This is
    # a lightweight diagnostic stage; it does not claim to perform 360-aware
    # reframing or highlight selection.
    proxy_files = (
        sorted(path for path in PROXY_ROOT.rglob("*.mp4") if is_media_file(path))
        if PROXY_ROOT.exists()
        else []
    )
    if not proxy_files:
        print("\nAucun proxy trouvé après la génération.")
        return 1

    scenes_dir = Path("/mnt/video/02_WORK/scenes")
    for index, proxy in enumerate(proxy_files, start=1):
        output = scenes_dir / proxy.relative_to(PROXY_ROOT).with_suffix(".json")
        run_step(
            f"4/5 — Détection des scènes [{index}/{len(proxy_files)}]",
            [python, str(AGENT_DIR / "scenes.py"), str(proxy), "--output", str(output)],
        )

    run_step(
        "5/5 — Prototype Reel vertical",
        [python, str(AGENT_DIR / "test_pipeline.py")],
    )

    print("\n" + "=" * 72)
    print("PIPELINE TERMINÉ")
    print("=" * 72)
    print(f"Rushs source : {source}")
    print(f"Proxies      : {PROXY_ROOT}")
    print(f"Scènes       : {scenes_dir}")
    print("Prototype    : /mnt/video/03_EXPORT/test-project/prototype-reel.mp4")
    print("\nNote : le pipeline actuel ne fait pas encore le stitching 360 X5 ni le reframing 360 automatique.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as exc:
        print(f"\nERREUR : étape interrompue (code {exc.returncode}).", file=sys.stderr)
        raise SystemExit(exc.returncode)
