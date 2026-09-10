#!/usr/bin/env python3
"""Clone TradingAgents and install it into a virtualenv.

Idempotent: re-running pulls the latest commit and reinstalls in place.
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

REPO = "https://github.com/TauricResearch/TradingAgents.git"
DEFAULT_SRC = Path.home() / "TradingAgents"
DEFAULT_VENV = Path.home() / ".tradingagents-venv"


def run(cmd, **kw):
    print(f"$ {' '.join(str(c) for c in cmd)}", flush=True)
    return subprocess.run(cmd, **kw)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--src", type=Path, default=DEFAULT_SRC)
    ap.add_argument("--venv", type=Path, default=DEFAULT_VENV)
    args = ap.parse_args()

    if sys.version_info < (3, 10):
        sys.exit(f"TradingAgents needs Python 3.10+, this is {sys.version.split()[0]}.")

    src, venv = args.src.expanduser(), args.venv.expanduser()
    if (src / ".git").is_dir():
        print(f"Repo already at {src}, updating...")
        run(["git", "-C", str(src), "pull", "--ff-only"], check=False)
    else:
        src.parent.mkdir(parents=True, exist_ok=True)
        run(["git", "clone", REPO, str(src)], check=True)

    py = venv / "bin" / "python"
    if not py.exists():
        py = venv / "Scripts" / "python.exe"
    if not py.exists():
        run([sys.executable, "-m", "venv", str(venv)], check=True)
        py = venv / "bin" / "python"
        if not py.exists():
            py = venv / "Scripts" / "python.exe"
    else:
        print(f"Reusing venv at {venv}")

    run([str(py), "-m", "pip", "install", "-q", "--upgrade", "pip"], check=True)
    res = run([str(py), "-m", "pip", "install", "-e", str(src)])
    if res.returncode != 0:
        sys.exit("Install failed — see pip output above.")

    print(f"""
Installed. Source at {src}, venv at {venv}

Set one provider key before running (matching config['llm_provider']):
  export OPENAI_API_KEY=...      # or ANTHROPIC_API_KEY / GOOGLE_API_KEY
  export FRED_API_KEY=...        # optional, macro_data only

Price/fundamentals default to yfinance and need no key.

Next — costs nothing, makes no LLM calls:
  {py} .claude/skills/tradingagents/scripts/preflight.py
""")


if __name__ == "__main__":
    main()
