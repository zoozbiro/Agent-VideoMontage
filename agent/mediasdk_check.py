#!/usr/bin/env python3
"""Check whether the LXC is ready to use Insta360 MediaSDK."""
import json
import os
import platform
import shutil
from pathlib import Path

CANDIDATE_BINARIES = [
    "MediaSDKTest",
    "MediaSDK",
]
CANDIDATE_PATHS = [
    Path("/opt/Insta360"),
    Path("/opt/MediaSDK"),
    Path("/usr/local/Insta360"),
    Path("/usr/local/MediaSDK"),
    Path("/opt/insta360"),
]

def os_release() -> dict:
    data = {}
    path = Path("/etc/os-release")
    if path.exists():
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if "=" in line and not line.startswith("#"):
                key, value = line.split("=", 1)
                data[key] = value.strip().strip('"')
    return data

def main() -> None:
    release = os_release()
    binaries = {name: shutil.which(name) for name in CANDIDATE_BINARIES}
    candidate_dirs = [str(p) for p in CANDIDATE_PATHS if p.exists()]

    result = {
        "platform": {
            "system": platform.system(),
            "machine": platform.machine(),
            "distribution": release.get("PRETTY_NAME", release.get("NAME", "unknown")),
            "version_id": release.get("VERSION_ID"),
        },
        "graphics": {
            "render_device": "/dev/dri/renderD128" if Path("/dev/dri/renderD128").exists() else None,
            "dri_directory": str(Path("/dev/dri")) if Path("/dev/dri").exists() else None,
        },
        "commands": binaries,
        "candidate_sdk_directories": candidate_dirs,
        "status": "ready" if any(binaries.values()) else "sdk_not_found",
    }

    print(json.dumps(result, indent=2, ensure_ascii=False))
    print()
    if result["status"] == "ready":
        print("MediaSDK candidate detected: inspect its --help/version before wiring the stitcher.")
    else:
        print("No MediaSDK executable detected.")
        print("Do not install a guessed package: obtain the official Insta360 MediaSDK first.")
        print("The next implementation step is to validate the SDK/runtime, then build the X5 stitch wrapper.")

if __name__ == "__main__":
    main()
