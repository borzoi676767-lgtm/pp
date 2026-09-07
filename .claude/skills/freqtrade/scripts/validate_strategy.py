#!/usr/bin/env python3
"""Run freqtrade's three correctness checks on a strategy and summarize them.

A profitable backtest means little on its own. This runs, in order:

  1. backtesting          - the headline numbers
  2. lookahead-analysis   - does the strategy peek at future candles?
  3. recursive-analysis   - do indicators change value depending on how much
                            warm-up history they were fed?

A lookahead hit means the backtest is fiction. A recursive hit means the
indicator will behave differently live than it did in backtest. Either one
invalidates the profit numbers, so read the verdict before the metrics.
"""
import argparse
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

DEFAULT_VENV = Path.home() / ".freqtrade-venv"
ANSI = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]")


def ensure_freqtrade_importable():
    """Re-exec under the freqtrade venv if this interpreter lacks freqtrade."""
    try:
        import freqtrade  # noqa: F401
        return
    except ImportError:
        pass
    venv_py = DEFAULT_VENV / "bin" / "python"
    if not venv_py.exists():                        # Windows layout
        venv_py = DEFAULT_VENV / "Scripts" / "python.exe"
    # Compare sys.prefix, not the interpreter path: a venv's bin/python is a
    # symlink to the base interpreter, so resolve() would make every path look
    # like the same file and the re-exec would never happen. The env marker is a
    # second guard against exec-looping if the venv somehow lacks freqtrade.
    already_tried = os.environ.get("_FT_VALIDATE_REEXEC") == "1"
    if venv_py.exists() and not already_tried and \
            Path(sys.prefix).resolve() != DEFAULT_VENV.resolve():
        os.environ["_FT_VALIDATE_REEXEC"] = "1"
        os.execve(str(venv_py), [str(venv_py), os.path.abspath(__file__), *sys.argv[1:]],
                  os.environ)
    sys.exit(f"freqtrade is not importable, and {DEFAULT_VENV} does not provide it. "
             "Run scripts/setup_freqtrade.py first, or invoke this script with the "
             "python that has freqtrade installed.")


def ft(args, common, capture=True):
    cmd = [sys.executable, "-m", "freqtrade", *args, *common, "--no-color"]
    print(f"\n$ {' '.join(cmd[2:])}", flush=True)
    res = subprocess.run(cmd, capture_output=capture, text=True)
    if capture:
        return res.returncode, ANSI.sub("", res.stdout or ""), ANSI.sub("", res.stderr or "")
    return res.returncode, "", ""


def fail_hint(stderr):
    """Turn freqtrade's known config errors into actionable advice."""
    hints = [
        ("price_side", 'lookahead-analysis forces market orders, which need '
                       '"entry_pricing"/"exit_pricing" -> "price_side": "other" in the config.'),
        ("Please set a timerange", "lookahead-analysis requires --timerange."),
        ("more than 5x", "recursive-analysis asked for more startup candles than the exchange "
                         "serves. Pass a smaller set, e.g. --startup-candle 199 399 999."),
        ("No data found", "No candles on disk for that timerange. Run freqtrade download-data "
                          "for these pairs/timeframe first."),
    ]
    tail = stderr.strip().splitlines()[-6:]
    for needle, advice in hints:
        if needle in stderr:
            return advice, tail
    return None, tail


def run_backtest(common, args):
    with tempfile.TemporaryDirectory() as td:
        rc, out, err = ft(["backtesting", "--strategy", args.strategy,
                           "--export", "trades", "--backtest-directory", td], common)
        if rc != 0:
            advice, tail = fail_hint(err)
            return {"ok": False, "advice": advice, "tail": tail}
        from freqtrade.data.btanalysis import load_backtest_stats
        try:
            stats = load_backtest_stats(Path(td))
            s = stats["strategy"][args.strategy]
        except Exception as exc:                      # noqa: BLE001
            return {"ok": False, "advice": f"Could not read backtest results: {exc}", "tail": []}
        return {"ok": True, "stats": s}


def run_lookahead(common, args):
    with tempfile.TemporaryDirectory() as td:
        csv = Path(td) / "lookahead.csv"
        extra = ["--lookahead-analysis-exportfilename", str(csv)]
        if args.minimum_trade_amount:
            extra += ["--minimum-trade-amount", str(args.minimum_trade_amount)]
        rc, out, err = ft(["lookahead-analysis", "--strategy", args.strategy, *extra], common)
        if not csv.exists():
            advice, tail = fail_hint(err + out)
            return {"ok": False, "advice": advice, "tail": tail}
        import pandas as pd
        df = pd.read_csv(csv)
        row = df[df["strategy"] == args.strategy]
        if row.empty:
            return {"ok": False, "advice": "lookahead-analysis produced no row for this "
                                           "strategy (often too few signals in the timerange).",
                    "tail": (err or out).strip().splitlines()[-6:]}
        r = row.iloc[-1]
        return {"ok": True, "has_bias": bool(r["has_bias"]),
                "total_signals": int(r["total_signals"]),
                "entry": int(r["biased_entry_signals"]), "exit": int(r["biased_exit_signals"]),
                "indicators": str(r["biased_indicators"]) if str(r["biased_indicators"]) != "nan" else ""}


def parse_recursive(out):
    """Pull (indicator, [pct...]) rows out of the rich table on stdout."""
    rows, header = [], []
    for line in out.splitlines():
        if "│" not in line:
            continue
        cells = [c.strip() for c in line.strip().strip("│").split("│")]
        if len(cells) < 2:
            continue
        if not header and not cells[0].endswith("%") and "%" not in "".join(cells[1:]):
            header = cells
            continue
        vals = []
        for c in cells[1:]:
            if c.endswith("%") and c not in ("nan%",):
                try:
                    vals.append(abs(float(c.rstrip("%"))))
                except ValueError:
                    pass
        if vals:
            rows.append((cells[0], cells[1:], max(vals)))
    return header, rows


FOUND_LOOKAHEAD = re.compile(r"found lookahead in indicator (\S+)")


def run_recursive(common, args):
    extra = []
    if args.startup_candle:
        extra = ["--startup-candle", *[str(c) for c in args.startup_candle]]
    rc, out, err = ft(["recursive-analysis", "--strategy", args.strategy, *extra], common)
    blob = out + err
    header, rows = parse_recursive(blob)
    # recursive-analysis has a second mode: when indicators show no variance it
    # switches to checking them for outright lookahead and prints no table. That
    # is a real result, not a failure.
    peeking = sorted(set(FOUND_LOOKAHEAD.findall(blob)))
    no_variance = "No variance on indicator(s) found" in blob
    if not rows and not peeking and not no_variance:
        advice, tail = fail_hint(blob)
        return {"ok": False, "advice": advice, "tail": tail}
    flagged = [(n, v, m) for n, v, m in rows if m >= args.recursive_threshold]
    return {"ok": True, "header": header, "rows": rows, "flagged": flagged,
            "peeking": peeking, "no_variance": no_variance}


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--strategy", required=True)
    ap.add_argument("-c", "--config", action="append", default=[],
                    help="config file (repeatable)")
    ap.add_argument("--userdir", default=None)
    ap.add_argument("--datadir", default=None)
    ap.add_argument("--strategy-path", default=None)
    ap.add_argument("--timerange", default=None,
                    help="e.g. 20240101-20240630. Required by lookahead-analysis.")
    ap.add_argument("--timeframe", default=None)
    ap.add_argument("-p", "--pairs", nargs="+", default=None)
    ap.add_argument("--startup-candle", nargs="+", type=int, default=[199, 399, 999],
                    help="warm-up sizes for recursive-analysis (default: 199 399 999; the "
                         "built-in default includes 1999, which some exchanges will not serve)")
    ap.add_argument("--recursive-threshold", type=float, default=0.5,
                    help="flag indicators drifting more than this percent (default: 0.5)")
    ap.add_argument("--minimum-trade-amount", type=int, default=None)
    ap.add_argument("--skip", nargs="+", default=[],
                    choices=["backtest", "lookahead", "recursive"])
    args = ap.parse_args()

    common = []
    for c in args.config:
        common += ["-c", c]
    for flag, val in (("--userdir", args.userdir), ("--datadir", args.datadir),
                      ("--strategy-path", args.strategy_path),
                      ("--timerange", args.timerange), ("--timeframe", args.timeframe)):
        if val:
            common += [flag, val]
    if args.pairs:
        common += ["-p", *args.pairs]

    if not args.timerange and "lookahead" not in args.skip:
        print("Note: lookahead-analysis requires --timerange; it will fail without one.\n")

    results = {}
    if "backtest" not in args.skip:
        results["backtest"] = run_backtest(common, args)
    if "lookahead" not in args.skip:
        results["lookahead"] = run_lookahead(common, args)
    if "recursive" not in args.skip:
        results["recursive"] = run_recursive(common, args)

    print("\n" + "=" * 72)
    print(f"VALIDATION SUMMARY — {args.strategy}"
          + (f"  [{args.timerange}]" if args.timerange else ""))
    print("=" * 72)

    bt = results.get("backtest")
    if bt and bt["ok"]:
        s = bt["stats"]
        def g(k, default="n/a"):
            return s.get(k, default)
        print("\nBacktest")
        print(f"  trades              {g('total_trades')}   over {g('backtest_days')} days")
        print(f"  total profit        {float(g('profit_total', 0)) * 100:.2f}%  "
              f"({g('profit_total_abs')} {s.get('stake_currency', '')})")
        print(f"  win rate            {float(g('winrate', 0)) * 100:.1f}%")
        print(f"  max drawdown        {float(g('max_drawdown_account', 0)) * 100:.2f}%")
        print(f"  profit factor       {g('profit_factor')}")
        print(f"  sharpe / sortino    {g('sharpe')} / {g('sortino')}")
        if isinstance(g('total_trades', 0), int) and g('total_trades', 0) < 30:
            print("  ! Fewer than ~30 trades — these statistics are noise, not evidence.")
    elif bt:
        print(f"\nBacktest FAILED. {bt.get('advice') or ''}".rstrip())
        for line in bt["tail"]:
            print(f"    {line}")

    la = results.get("lookahead")
    if la and la["ok"]:
        print("\nLookahead analysis")
        if la["has_bias"]:
            print(f"  *** BIAS DETECTED *** over {la['total_signals']} signals")
            print(f"  biased entry signals: {la['entry']}, exit signals: {la['exit']}")
            if la["indicators"]:
                print(f"  suspect indicators:   {la['indicators']}")
            print("  The strategy sees data it could not have had at that moment. The backtest")
            print("  numbers above are meaningless until this is fixed. Look for .shift(-n),")
            print("  negative-shift comparisons, df.iloc[-1] on the full frame, resampling")
            print("  without label/closed alignment, or indicators computed over the whole set.")
        else:
            print(f"  no bias detected over {la['total_signals']} signals")
    elif la:
        print(f"\nLookahead analysis FAILED. {la.get('advice') or ''}".rstrip())
        for line in la["tail"]:
            print(f"    {line}")

    rc = results.get("recursive")
    if rc and rc["ok"]:
        print("\nRecursive analysis (indicator drift by warm-up size)")
        if rc["peeking"]:
            print(f"  *** INDICATOR LOOKAHEAD *** {', '.join(rc['peeking'])}")
            print("  These indicators read values from candles after the one being computed.")
        if rc["no_variance"] and not rc["rows"]:
            print("  no variance across warm-up sizes (nothing to compare)")
        if rc["flagged"]:
            print(f"  {len(rc['flagged'])} indicator(s) drift more than "
                  f"{args.recursive_threshold}%:")
            for name, vals, worst in sorted(rc["flagged"], key=lambda r: -r[2]):
                print(f"    {name:<18} worst {worst:.3f}%   ({', '.join(vals)})")
            print("  These need more startup candles than the strategy currently requests.")
            print("  Raise startup_candle_count until the drift settles.")
        elif rc["rows"]:
            print(f"  no indicator drifts more than {args.recursive_threshold}%")
    elif rc:
        print(f"\nRecursive analysis FAILED. {rc.get('advice') or ''}".rstrip())
        for line in rc["tail"]:
            print(f"    {line}")

    print("\nVerdict")
    fatal, serious = [], []
    if la and la.get("ok") and la["has_bias"]:
        fatal.append("lookahead bias")
    if rc and rc.get("ok") and rc.get("peeking"):
        fatal.append("indicators reading future candles")
    if rc and rc.get("ok") and rc["flagged"]:
        serious.append("indicator warm-up drift")
    if fatal:
        print(f"  FICTION — {' and '.join(fatal)}.")
        print("  The strategy uses data it could not have had in real time, so the profit")
        print("  numbers describe nothing. Fix this first; every other metric is downstream.")
        sys.exit(1)
    if serious:
        print(f"  UNRELIABLE — {' and '.join(serious)}.")
        print("  Indicators settle at different values depending on warm-up, so live")
        print("  behavior will diverge from this backtest.")
        print("  Raise startup_candle_count and re-run before trusting the numbers.")
        sys.exit(1)
    if any(r and not r.get("ok") for r in results.values()):
        print("  INCOMPLETE — at least one check did not run. See the failures above.")
        sys.exit(2)
    print("  Checks passed. That rules out two specific bugs; it does not mean the strategy")
    print("  is profitable. Confirm on an untouched period, then dry-run for weeks.")


if __name__ == "__main__":
    ensure_freqtrade_importable()
    main()
