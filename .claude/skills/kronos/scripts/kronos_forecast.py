#!/usr/bin/env python3
"""Forecast OHLCV candlesticks with Kronos.

Reads a CSV of historical bars, samples one or more future paths, writes the
result to CSV and optionally plots it. With --backtest it forecasts a window
that already has ground truth and scores the result.

Examples:
    # 24 bars ahead with an uncertainty band
    kronos_forecast.py --csv btc_1h.csv --lookback 400 --pred-len 24 \
        --paths 30 --out fc.csv --plot fc.png

    # sanity-check the model on this instrument first
    kronos_forecast.py --csv btc_1h.csv --lookback 400 --pred-len 24 \
        --paths 30 --backtest --plot bt.png
"""
import argparse
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# Model / tokenizer pairings and context limits, from the Kronos model card.
PRESETS = {
    "mini":  ("NeoQuasar/Kronos-mini",  "NeoQuasar/Kronos-Tokenizer-2k",   2048),
    "small": ("NeoQuasar/Kronos-small", "NeoQuasar/Kronos-Tokenizer-base",  512),
    "base":  ("NeoQuasar/Kronos-base",  "NeoQuasar/Kronos-Tokenizer-base",  512),
}
TS_CANDIDATES = ["timestamps", "timestamp", "date", "datetime", "time"]
PRICE_COLS = ["open", "high", "low", "close"]


def load_kronos():
    home = Path(os.environ.get("KRONOS_HOME", Path.home() / ".kronos" / "Kronos")).expanduser()
    if not (home / "model").is_dir():
        sys.exit(f"Kronos not found at {home}. Run scripts/setup_kronos.py first "
                 f"(or set KRONOS_HOME to an existing checkout).")
    sys.path.insert(0, str(home))
    from model import Kronos, KronosTokenizer, KronosPredictor  # noqa: E402
    return Kronos, KronosTokenizer, KronosPredictor


def read_bars(path, ts_col):
    df = pd.read_csv(path)
    lower = {c.lower().strip(): c for c in df.columns}
    if ts_col is None:
        for cand in TS_CANDIDATES:
            if cand in lower:
                ts_col = lower[cand]
                break
        else:
            sys.exit(f"No timestamp column found in {path}. Columns: {list(df.columns)}. "
                     f"Pass --timestamp-col.")
    elif ts_col not in df.columns:
        sys.exit(f"--timestamp-col {ts_col!r} not in {list(df.columns)}")

    df = df.rename(columns={lower[k]: k for k in lower if k in PRICE_COLS + ["volume", "amount"]})
    missing = [c for c in PRICE_COLS if c not in df.columns]
    if missing:
        sys.exit(f"CSV is missing required price columns: {missing}")

    df["_ts"] = pd.to_datetime(df[ts_col])
    df = df.sort_values("_ts").reset_index(drop=True)
    keep = PRICE_COLS + [c for c in ("volume", "amount") if c in df.columns]
    return df[["_ts"] + keep].dropna(subset=PRICE_COLS).reset_index(drop=True)


def future_timestamps(hist_ts, n, freq=None):
    """Extend a timestamp series by n steps.

    Note this walks in uniform steps, so for intraday equity data it will happily
    invent bars inside the overnight gap. When exact session timestamps matter,
    pass --freq or supply the future rows in the CSV and use --backtest.
    """
    idx = pd.DatetimeIndex(hist_ts)
    if freq:
        off = pd.tseries.frequencies.to_offset(freq)
    else:
        inferred = pd.infer_freq(idx[-min(len(idx), 50):])
        if inferred:
            off = pd.tseries.frequencies.to_offset(inferred)
        else:
            off = pd.Timedelta(np.median(np.diff(idx.values)))
    return pd.Series([idx[-1] + off * (i + 1) for i in range(n)])


def metrics(pred_close, true_close, anchor):
    err = pred_close - true_close
    out = {
        "mae": float(np.mean(np.abs(err))),
        "rmse": float(np.sqrt(np.mean(err ** 2))),
        "mape_pct": float(np.mean(np.abs(err / true_close)) * 100),
    }
    p = np.sign(np.diff(np.concatenate([[anchor], pred_close])))
    t = np.sign(np.diff(np.concatenate([[anchor], true_close])))
    out["directional_acc_pct"] = float(np.mean(p == t) * 100)
    return out


def plot(hist, med, band, actual, path, title):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    tail = hist.tail(max(len(med) * 3, 60))
    has_vol = "volume" in hist.columns and "volume" in med.columns
    fig, axes = plt.subplots(2 if has_vol else 1, 1, figsize=(11, 7 if has_vol else 4.5),
                             sharex=True, squeeze=False)
    ax = axes[0][0]
    ax.plot(tail["_ts"], tail["close"], color="#1f77b4", lw=1.4, label="History")
    ax.plot(med.index, med["close"], color="#d62728", lw=1.6, label="Forecast (median)")
    if band is not None:
        ax.fill_between(med.index, band[0], band[1], color="#d62728", alpha=0.18,
                        label="p10-p90")
    if actual is not None:
        ax.plot(actual["_ts"], actual["close"], color="#2ca02c", lw=1.4, label="Actual")
    ax.set_ylabel("Close")
    ax.set_title(title)
    ax.legend(loc="best", fontsize=9)
    ax.grid(alpha=0.3)

    if has_vol:
        ax2 = axes[1][0]
        ax2.plot(tail["_ts"], tail["volume"], color="#1f77b4", lw=1.1)
        ax2.plot(med.index, med["volume"], color="#d62728", lw=1.3)
        if actual is not None and "volume" in actual.columns:
            ax2.plot(actual["_ts"], actual["volume"], color="#2ca02c", lw=1.1)
        ax2.set_ylabel("Volume")
        ax2.grid(alpha=0.3)

    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    print(f"Plot written to {path}")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csv", required=True, help="CSV of historical OHLCV bars")
    ap.add_argument("--timestamp-col", default=None)
    ap.add_argument("--model", default="small",
                    help="preset (mini|small|base) or a HuggingFace model id")
    ap.add_argument("--tokenizer", default=None,
                    help="override the tokenizer id (required with a custom --model)")
    ap.add_argument("--max-context", type=int, default=None)
    ap.add_argument("--lookback", type=int, default=400, help="history bars fed to the model")
    ap.add_argument("--pred-len", type=int, default=24, help="bars to forecast")
    ap.add_argument("--paths", type=int, default=1,
                    help="independent sampled futures; >=20 for usable p10/p90 bands")
    ap.add_argument("--T", type=float, default=1.0, dest="temperature")
    ap.add_argument("--top-p", type=float, default=0.9)
    ap.add_argument("--top-k", type=int, default=0)
    ap.add_argument("--sample-count", type=int, default=1,
                    help="paths averaged *inside* one predict call (smooths each path)")
    ap.add_argument("--device", default=None, help="cuda:0 | mps | cpu (auto if omitted)")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--freq", default=None, help="pandas offset alias for future bars, e.g. 5min")
    ap.add_argument("--backtest", action="store_true",
                    help="forecast the last --pred-len rows of the CSV and score them")
    ap.add_argument("--out", default=None, help="write the forecast CSV here")
    ap.add_argument("--plot", default=None, help="write a PNG chart here")
    args = ap.parse_args()

    if args.model in PRESETS:
        model_id, tok_id, ctx = PRESETS[args.model]
    else:
        model_id, tok_id, ctx = args.model, args.tokenizer, 512
        if tok_id is None:
            sys.exit("--tokenizer is required when --model is a raw HuggingFace id")
    max_context = args.max_context or ctx
    if args.lookback > max_context:
        print(f"Warning: --lookback {args.lookback} exceeds the {max_context}-bar context of "
              f"{model_id}; the predictor will truncate to the most recent {max_context} bars.")

    bars = read_bars(args.csv, args.timestamp_col)
    need = args.lookback + (args.pred_len if args.backtest else 0)
    if len(bars) < need:
        sys.exit(f"CSV has {len(bars)} usable rows, need {need} "
                 f"(lookback{'+pred_len' if args.backtest else ''}).")

    if args.backtest:
        hist = bars.iloc[-need:-args.pred_len].reset_index(drop=True)
        actual = bars.iloc[-args.pred_len:].reset_index(drop=True)
        y_timestamp = actual["_ts"].reset_index(drop=True).rename("timestamp")
    else:
        hist = bars.iloc[-args.lookback:].reset_index(drop=True)
        actual = None
        y_timestamp = future_timestamps(hist["_ts"], args.pred_len, args.freq).rename("timestamp")

    Kronos, KronosTokenizer, KronosPredictor = load_kronos()
    import torch

    print(f"Loading {model_id} + {tok_id} ...")
    tokenizer = KronosTokenizer.from_pretrained(tok_id)
    model = Kronos.from_pretrained(model_id)
    predictor = KronosPredictor(model, tokenizer, device=args.device, max_context=max_context)
    print(f"Device: {predictor.device} | lookback {len(hist)} | pred_len {args.pred_len} "
          f"| paths {args.paths}")

    x_df = hist[[c for c in PRICE_COLS + ["volume", "amount"] if c in hist.columns]]
    x_timestamp = hist["_ts"]

    preds = []
    for i in range(args.paths):
        if args.seed is not None:
            torch.manual_seed(args.seed + i)
        preds.append(predictor.predict(
            df=x_df, x_timestamp=x_timestamp, y_timestamp=y_timestamp,
            pred_len=args.pred_len, T=args.temperature, top_k=args.top_k,
            top_p=args.top_p, sample_count=args.sample_count,
            verbose=(args.paths == 1),
        ))
        if args.paths > 1:
            print(f"  path {i + 1}/{args.paths}", flush=True)

    stack = np.stack([p.values for p in preds])          # (paths, pred_len, 6)
    med = pd.DataFrame(np.median(stack, axis=0), columns=preds[0].columns,
                       index=pd.DatetimeIndex(y_timestamp, name="timestamp"))
    band = None
    if args.paths > 1:
        ci = preds[0].columns.get_loc("close")
        band = (np.percentile(stack[:, :, ci], 10, axis=0),
                np.percentile(stack[:, :, ci], 90, axis=0))

    out_df = med.copy()
    out_df.index.name = "timestamp"
    if band is not None:
        out_df["close_p10"], out_df["close_p90"] = band
        for i, p in enumerate(preds):
            out_df[f"close_path{i}"] = p["close"].values
    if actual is not None:
        out_df["close_actual"] = actual["close"].values

    print("\nForecast (median path):")
    print(med.head(10).to_string())

    if actual is not None:
        m = metrics(med["close"].values, actual["close"].values, hist["close"].iloc[-1])
        print("\nBacktest vs ground truth (close):")
        for k, v in m.items():
            print(f"  {k:>20}: {v:.4f}")
        print("  Directional accuracy near 50% means no usable signal on this series.")

    if args.out:
        out_df.to_csv(args.out)
        print(f"\nForecast written to {args.out}")
    if args.plot:
        title = (f"{Path(args.csv).stem} — Kronos-{args.model} "
                 f"{'backtest' if args.backtest else 'forecast'} "
                 f"({args.pred_len} bars, {args.paths} path{'s' if args.paths > 1 else ''})")
        plot(hist, med, band, actual, args.plot, title)


if __name__ == "__main__":
    main()
