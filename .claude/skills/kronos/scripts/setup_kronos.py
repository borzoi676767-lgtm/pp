#!/usr/bin/env python3
"""Clone the Kronos repo and install its dependencies.

Idempotent: re-running pulls the latest commit and lets pip skip satisfied
requirements. The checkout location defaults to ~/.kronos/Kronos and can be
overridden with the KRONOS_HOME environment variable.
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

REPO_URL = "https://github.com/shiyu-coder/Kronos.git"
DEFAULT_HOME = Path(os.environ.get("KRONOS_HOME", Path.home() / ".kronos" / "Kronos"))


def run(cmd, **kwargs):
    print(f"$ {' '.join(str(c) for c in cmd)}", flush=True)
    subprocess.run(cmd, check=True, **kwargs)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--home", type=Path, default=DEFAULT_HOME,
                    help=f"where to check out Kronos (default: {DEFAULT_HOME})")
    ap.add_argument("--no-deps", action="store_true",
                    help="clone only, skip pip install")
    args = ap.parse_args()

    home = args.home.expanduser()
    if (home / ".git").is_dir():
        print(f"Kronos already at {home}, updating...")
        run(["git", "-C", str(home), "pull", "--ff-only"])
    else:
        home.parent.mkdir(parents=True, exist_ok=True)
        run(["git", "clone", "--depth", "1", REPO_URL, str(home)])

    if not args.no_deps:
        req = home / "requirements.txt"
        # The pinned requirements.txt is strict about matplotlib/pandas versions,
        # which often collides with an existing environment. Install the loose
        # set the model code actually imports, and only fall back to the pinned
        # file if that fails.
        loose = ["numpy", "pandas", "torch>=2.0.0", "einops",
                 "huggingface_hub", "safetensors", "matplotlib", "tqdm"]
        try:
            run([sys.executable, "-m", "pip", "install", "-q", *loose])
        except subprocess.CalledProcessError:
            print("Loose install failed; falling back to pinned requirements.txt")
            run([sys.executable, "-m", "pip", "install", "-q", "-r", str(req)])

    print(f"\nKronos ready at {home}")
    print("Weights download from HuggingFace on first forecast (NeoQuasar/Kronos-*).")
    if "KRONOS_HOME" not in os.environ and home != DEFAULT_HOME:
        print(f"Set KRONOS_HOME={home} so the forecast script finds this checkout.")


if __name__ == "__main__":
    main()
