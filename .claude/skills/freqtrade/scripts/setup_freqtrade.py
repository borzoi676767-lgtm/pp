#!/usr/bin/env python3
"""Install freqtrade into a virtualenv and initialize a user_data directory.

Idempotent: reuses an existing venv and lets pip skip satisfied requirements.
"""
import argparse
import subprocess
import sys
from pathlib import Path

DEFAULT_VENV = Path.home() / ".freqtrade-venv"
TALIB_HELP = """
The install failed while building TA-Lib, the C library the Python bindings wrap.
Recent freqtrade releases install a TA-Lib wheel with no compiler needed, so this
usually means an unusual platform. Two paths that work:

  1. The repo's own installer, which builds TA-Lib for you:
       git clone https://github.com/freqtrade/freqtrade.git && cd freqtrade
       ./setup.sh -i
  2. Docker, which sidesteps the build entirely:
       https://www.freqtrade.io/en/stable/docker_quickstart/

Hand-compiling TA-Lib is not worth the time; use one of the above.
"""


def run(cmd, **kw):
    print(f"$ {' '.join(str(c) for c in cmd)}", flush=True)
    return subprocess.run(cmd, **kw)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--venv", type=Path, default=DEFAULT_VENV,
                    help=f"virtualenv location (default: {DEFAULT_VENV})")
    ap.add_argument("--userdir", type=Path, default=Path("user_data"),
                    help="where to create the user_data directory (default: ./user_data)")
    ap.add_argument("--hyperopt", action="store_true", help="include optimization extras")
    ap.add_argument("--plot", action="store_true", help="include plotly plotting extras")
    ap.add_argument("--freqai", action="store_true", help="include FreqAI ML extras")
    ap.add_argument("--no-userdir", action="store_true", help="skip create-userdir")
    args = ap.parse_args()

    if sys.version_info < (3, 11):
        sys.exit(f"freqtrade needs Python 3.11+, this is {sys.version.split()[0]}. "
                 f"Install a newer Python and re-run with it.")

    venv = args.venv.expanduser()
    py = venv / "bin" / "python"
    if not py.exists():                       # Windows layout
        py = venv / "Scripts" / "python.exe"
    if not py.exists():
        run([sys.executable, "-m", "venv", str(venv)], check=True)
        py = (venv / "bin" / "python")
        if not py.exists():
            py = venv / "Scripts" / "python.exe"
    else:
        print(f"Reusing existing venv at {venv}")

    extras = [n for n, on in (("hyperopt", args.hyperopt), ("plot", args.plot),
                              ("freqai", args.freqai)) if on]
    target = f"freqtrade[{','.join(extras)}]" if extras else "freqtrade"

    run([str(py), "-m", "pip", "install", "-q", "--upgrade", "pip"], check=True)
    res = run([str(py), "-m", "pip", "install", target])
    if res.returncode != 0:
        print(TALIB_HELP, file=sys.stderr)
        sys.exit(res.returncode)

    ft = py.parent / "freqtrade"
    if not args.no_userdir:
        userdir = args.userdir.expanduser()
        if userdir.exists():
            print(f"{userdir} already exists, leaving it alone.")
        else:
            run([str(ft), "create-userdir", "--userdir", str(userdir)], check=True)

    run([str(ft), "--version"], check=False)
    print(f"""
freqtrade installed at {ft}

  Activate:   source {venv}/bin/activate
  Or call:    {ft} <command>

Next:
  freqtrade new-config --config {args.userdir}/config.json     # interactive, keeps dry_run on
  freqtrade new-strategy --strategy MyStrategy
  freqtrade download-data --exchange binance --pairs BTC/USDT --timeframes 5m --days 90
""")


if __name__ == "__main__":
    main()
