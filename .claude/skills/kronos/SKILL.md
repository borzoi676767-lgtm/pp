---
name: kronos
description: Forecast financial OHLCV candlesticks (K-lines) with Kronos, an open-source foundation model for market data (github.com/shiyu-coder/Kronos). Use this whenever the user wants to predict, forecast, or extrapolate price/volume bars for a stock, crypto pair, futures contract or index — including phrases like "predict the next N candles", "forecast BTC for the next 24h", "where is this ticker heading", "run a K-line model on this CSV", "backtest a price forecast", or when they hand over an OHLCV CSV and ask what happens next. Also use it for sampling multiple forecast paths / uncertainty bands from price history, and for finetuning Kronos on custom market data.
---

# Kronos: K-line forecasting

Kronos is a decoder-only foundation model trained on candlesticks from 45+ exchanges. It
tokenizes OHLCV bars with a learned quantizer, then autoregressively samples continuations —
so it is a *generative* forecaster, not a point predictor. Two consequences shape everything
below: a single forecast is one sampled path (rerunning gives a different answer), and the
useful output is a distribution over paths rather than a single line.

## Setup

The model code is a plain Python repo, not a pip package. Install it once:

```bash
python .claude/skills/kronos/scripts/setup_kronos.py
```

This clones the repo to `~/.kronos/Kronos` (override with `KRONOS_HOME`) and installs
torch, pandas, einops, huggingface_hub, safetensors, matplotlib. Weights download from
HuggingFace on first use, so the machine needs network access to `huggingface.co`.
Re-running is safe — it pulls and skips already-satisfied installs.

## Forecasting

Use the bundled script rather than writing inference code by hand; it handles the parts that
are easy to get subtly wrong (timestamp features, normalization windows, future-timestamp
generation, path sampling).

```bash
python .claude/skills/kronos/scripts/kronos_forecast.py \
  --csv data/btc_1h.csv --lookback 400 --pred-len 24 \
  --paths 30 --out forecast.csv --plot forecast.png
```

The input CSV needs a timestamp column (auto-detected among `timestamps`, `timestamp`,
`date`, `datetime`, `time`, or set `--timestamp-col`) plus `open,high,low,close`. `volume`
and `amount` are optional — Kronos was trained with them and predicts more sharply when
they are present, but the script fills them in when missing.

Key flags:

| Flag | Meaning |
| --- | --- |
| `--model mini\|small\|base` | Preset that pairs the right tokenizer and context length. `small` (24.7M) is the default and a good speed/quality balance; `base` (102.3M) is stronger; `mini` (4.1M) has a 2048-bar context for long histories. |
| `--lookback` | History bars fed in. Stay at or under the model's context (512 for small/base, 2048 for mini) — longer input is silently truncated. |
| `--pred-len` | Bars to forecast. |
| `--paths` | Independent sampled futures. Anything above ~20 gives usable p10/p50/p90 bands; 1 gives a single path and no uncertainty. |
| `--T`, `--top-p`, `--top-k` | Sampling temperature and nucleus/top-k truncation. Lower `T` (0.6–0.8) yields tamer, more mean-reverting paths; the 1.0 / 0.9 default is what the authors report. |
| `--backtest` | Hold out the last `--pred-len` real bars instead of forecasting past the end, and score against them. |
| `--device` | `cuda:0`, `mps`, `cpu`. Auto-detected when omitted. |

Outputs: a CSV of the median path (plus per-path columns when `--paths > 1`) and, with
`--plot`, a close-price chart with the uncertainty band and the volume panel.

**Always prefer `--backtest` before quoting a forward forecast.** It runs the identical
setup one window earlier where ground truth exists and reports MAE, RMSE, MAPE and
directional accuracy, which tells you whether the model is tracking this instrument at all.
Directional accuracy near 50% means the forecast carries no usable signal for that series —
say so rather than narrating the shape of the median path.

## Reading the output honestly

The median path looks confident and smooth; that smoothness is an averaging artifact, not
model conviction. When reporting results, lead with the band and the backtest metrics, quote
the median as one scenario among many, and keep in mind that a foundation model trained on
historical bars has no knowledge of news, earnings, or regime breaks after its training data.
Financial forecasts are not investment advice, and it is worth saying so once when the user
is clearly acting on the numbers.

## Free-running the API

When the script's shape doesn't fit — batch forecasting many tickers, embedding Kronos in a
backtest engine, custom normalization — call the model directly:

```python
import sys; sys.path.append("~/.kronos/Kronos")   # expanduser it
from model import Kronos, KronosTokenizer, KronosPredictor

tokenizer = KronosTokenizer.from_pretrained("NeoQuasar/Kronos-Tokenizer-base")
model = Kronos.from_pretrained("NeoQuasar/Kronos-small")
predictor = KronosPredictor(model, tokenizer, max_context=512)

pred_df = predictor.predict(
    df=x_df,                      # columns: open, high, low, close[, volume, amount]
    x_timestamp=x_timestamp,      # datetime Series, len == len(x_df)
    y_timestamp=y_timestamp,      # datetime Series, len == pred_len
    pred_len=120, T=1.0, top_p=0.9, sample_count=1,
)
```

`predictor.predict_batch(df_list, x_timestamp_list, y_timestamp_list, pred_len, ...)` runs
many series in parallel on one GPU pass, but requires every series to share the same history
length and `pred_len`.

`references/api.md` has the full parameter reference, model/tokenizer pairings, the exact
preprocessing the predictor applies, and pointers into the repo's finetuning pipeline. Read
it when finetuning on custom data or when a call is behaving unexpectedly.
