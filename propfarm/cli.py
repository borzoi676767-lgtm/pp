from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from .data import load_csv, synthetic
from .farm import Farm, load_config, load_data
from .rules import resolve
from .stats import monte_carlo, trade_stats


def print_report(farm: Farm) -> None:
    hdr = f"{'account':<16}{'status':<8}{'trades':>7}{'win%':>7}{'PF':>6}{'expR':>7}{'net':>11}{'maxDD':>10}{'days':>6}  note"
    print(hdr)
    print("-" * len(hdr))
    for a in farm.accounts:
        s = trade_stats(a.trades)
        pf = "inf" if s.profit_factor == float("inf") else f"{s.profit_factor:.2f}"
        note = a.status_reason or ("edge looks real" if s.edge() else "not enough evidence of edge")
        print(f"{a.name:<16}{a.status:<8}{s.trades:>7}{s.win_rate*100:>6.1f}%{pf:>6}{s.expectancy_r:>7.2f}"
              f"{s.net:>11,.0f}{a.max_drawdown:>10,.0f}{len(a.trading_days):>6}  {note}")
    print()
    counts = {st: sum(a.status == st for a in farm.accounts) for st in ("PASSED", "ACTIVE", "FAILED")}
    print("farm: " + ", ".join(f"{k.lower()} {v}" for k, v in counts.items())
          + f"; cross-account hedges blocked: {farm.blocked_hedges}")


def cmd_run(args) -> Farm:
    cfg_path = Path(args.config)
    cfg = load_config(cfg_path)
    if args.synthetic:
        syms = {a["symbol"] for a in cfg["accounts"]}
        shape = cfg.get("synthetic", {})
        data = {s: synthetic(days=args.days, seed=args.seed + i, **shape.get(s, {}))
                for i, s in enumerate(sorted(syms))}
    else:
        data = load_data(cfg, cfg_path.parent)
        for spec in args.data or []:
            sym, path = spec.split("=", 1)
            data[sym] = load_csv(path)
    farm = Farm.from_config(cfg)
    farm.run(data)
    print_report(farm)
    if args.json:
        out = [asdict(a.report()) for a in farm.accounts]
        Path(args.json).write_text(json.dumps(out, indent=2, default=str))
        print(f"wrote {args.json}")
    return farm


def cmd_montecarlo(args) -> None:
    farm = cmd_run(args)
    acct = next((a for a in farm.accounts if a.name == args.account), None)
    if acct is None:
        raise SystemExit(f"no account named {args.account!r}")
    rules = resolve(args.rules) if args.rules else acct.rules
    rs = [t.r_multiple for t in acct.trades]
    if not rs:
        raise SystemExit("account made no trades; nothing to resample")
    print(f"\nMonte Carlo for {acct.name} ({len(rs)} trades resampled) against {rules.firm} rules:")
    print(f"{'risk/trade':>11}{'pass':>8}{'fail':>8}{'open':>8}{'med trades':>12}")
    for risk in args.risk:
        r = monte_carlo(rs, rules, risk, trades_per_day=args.trades_per_day, runs=args.runs)
        med = f"{r.median_trades_to_pass:.0f}" if r.median_trades_to_pass else "-"
        print(f"{risk*100:>10.2f}%{r.pass_rate*100:>7.1f}%{r.fail_rate*100:>7.1f}%{r.unresolved_rate*100:>7.1f}%{med:>12}")


def main(argv=None) -> None:
    p = argparse.ArgumentParser(prog="propfarm", description="Simulate a farm of prop-firm accounts.")
    sub = p.add_subparsers(dest="cmd", required=True)

    def common(sp):
        sp.add_argument("--config", required=True)
        sp.add_argument("--data", action="append", metavar="SYMBOL=CSV", help="override/add a data file")
        sp.add_argument("--synthetic", action="store_true", help="use random-walk demo data")
        sp.add_argument("--days", type=int, default=250)
        sp.add_argument("--seed", type=int, default=7)
        sp.add_argument("--json", help="write per-account reports to this file")

    r = sub.add_parser("run", help="backtest every account in the config")
    common(r)
    r.set_defaults(func=cmd_run)

    m = sub.add_parser("montecarlo", help="estimate pass/fail odds from one account's trades")
    common(m)
    m.add_argument("--account", required=True)
    m.add_argument("--rules", help="rules preset to test against (default: the account's own)")
    m.add_argument("--risk", type=float, nargs="+", default=[0.0025, 0.005, 0.01, 0.02])
    m.add_argument("--trades-per-day", type=int, default=2)
    m.add_argument("--runs", type=int, default=5000)
    m.set_defaults(func=cmd_montecarlo)

    args = p.parse_args(argv)
    args.func(args)
