# Kronos API reference

Contents: [Models](#models) · [KronosPredictor](#kronospredictor) · [Preprocessing](#what-predict-does-to-your-data) · [Sampling](#sampling-parameters) · [Batch](#batch-prediction) · [Finetuning](#finetuning) · [Troubleshooting](#troubleshooting)

Upstream: https://github.com/shiyu-coder/Kronos

## Models

| Model | HuggingFace id | Tokenizer | Context | Params |
| --- | --- | --- | --- | --- |
| Kronos-mini | `NeoQuasar/Kronos-mini` | `NeoQuasar/Kronos-Tokenizer-2k` | 2048 | 4.1M |
| Kronos-small | `NeoQuasar/Kronos-small` | `NeoQuasar/Kronos-Tokenizer-base` | 512 | 24.7M |
| Kronos-base | `NeoQuasar/Kronos-base` | `NeoQuasar/Kronos-Tokenizer-base` | 512 | 102.3M |
| Kronos-large | — | `NeoQuasar/Kronos-Tokenizer-base` | 512 | 499.2M (not released) |

The tokenizer must match the model — a Tokenizer-base checkpoint feeding Kronos-mini
produces garbage rather than an error, because the token vocabularies differ.

Both classes use `PyTorchModelHubMixin`, so `from_pretrained` accepts a local directory
just as well as a hub id — that is how finetuned checkpoints are loaded back.

## KronosPredictor

```python
KronosPredictor(model, tokenizer, device=None, max_context=512, clip=5)
```

- `device` — `None` auto-selects `cuda:0`, then `mps`, then `cpu`. Both modules are moved
  onto it in `__init__`.
- `max_context` — bars of context the autoregressive loop keeps. Set it to the model's
  context length; longer inputs are truncated to the most recent `max_context` bars inside
  the generation loop, silently.
- `clip` — normalized values are clipped to ±`clip` before tokenization.

```python
predict(df, x_timestamp, y_timestamp, pred_len,
        T=1.0, top_k=0, top_p=0.9, sample_count=1, verbose=True) -> pd.DataFrame
```

- `df` — required columns `open, high, low, close`; optional `volume`, `amount`.
- `x_timestamp` — datetime Series aligned with `df` rows.
- `y_timestamp` — datetime Series of length `pred_len` for the bars being forecast. These
  are real inputs, not labels: the model conditions on their calendar features, so feeding
  timestamps that skip weekends or overnight gaps changes the forecast.
- Returns a DataFrame of `open, high, low, close, volume, amount` indexed by `y_timestamp`.

## What `predict` does to your data

Worth knowing, because it explains several surprises:

1. Missing `volume` → `volume` and `amount` are both filled with `0.0`. Missing `amount`
   alone → `amount = volume * mean(open, high, low, close)`.
2. Any NaN in the price/volume columns raises `ValueError`. Clean or forward-fill first.
3. Timestamps become five features: minute, hour, weekday, day, month. There is no year and
   no absolute time, so the model cannot know *which* 2019 it is looking at — only the
   shape of recent bars.
4. Each column is z-scored **over the input window only** (`x_mean`, `x_std` from those
   rows), clipped to ±5, and the prediction is de-normalized with the same statistics.
   A window with near-zero variance in some column (a halted stock, constant volume) gives
   that column a tiny std and wild de-normalized output.
5. There is no log transform. Prices are normalized in level space.

## Sampling parameters

- `T` (temperature) — scales logits before sampling. Below ~0.8 paths get smooth and
  mean-reverting; above ~1.2 they get volatile. 1.0 is the reported default.
- `top_p` — nucleus truncation, default 0.9. `top_k` defaults to 0 (disabled).
- `sample_count` — draws this many continuations **inside one call and averages them**
  (`np.mean` over the sample axis). It smooths a single path; it does not give you a
  distribution. For uncertainty bands call `predict` repeatedly with `sample_count=1` and
  take percentiles across calls — that is what `--paths` in `scripts/kronos_forecast.py`
  does. Note `sample_count > 1` multiplies the batch, so it costs roughly linearly in memory.
- `verbose` — tqdm progress bar over the autoregressive steps.

Reproducibility: `torch.manual_seed(n)` before each `predict` call fixes the sampled path.

## Batch prediction

```python
predict_batch(df_list, x_timestamp_list, y_timestamp_list, pred_len,
              T=1.0, top_k=0, top_p=0.9, sample_count=1, verbose=True) -> list[pd.DataFrame]
```

One GPU pass across many series — far faster than looping `predict` for a universe of
tickers. Every series must share the same `pred_len`, and each `y_timestamp_list[i]` must
have exactly `pred_len` entries, or it raises. Results come back in input order.

## Finetuning

The repo ships a four-stage pipeline under `finetune/` (Qlib-based, demonstrated on Chinese
A-shares) and a CSV-based variant under `finetune_csv/` that avoids the Qlib dependency.
The upstream README is explicit that this is a demonstration, not a production quant system.

1. Edit `finetune/config.py` — `qlib_data_path`, `dataset_path`, `save_path`,
   `backtest_result_path`, `pretrained_tokenizer_path`, `pretrained_predictor_path`,
   plus `instrument`, `train_time_range`, `epochs`, `batch_size`. Set `use_comet = False`
   unless you have a Comet.ml account.
2. `pip install pyqlib` and prepare Qlib data, then
   `python finetune/qlib_data_preprocess.py` → `train/val/test_data.pkl`.
3. `torchrun --standalone --nproc_per_node=N finetune/train_tokenizer.py`, then
   `torchrun --standalone --nproc_per_node=N finetune/train_predictor.py`. Tokenizer first —
   the predictor trains against the tokenizer's vocabulary.
4. `python finetune/qlib_test.py` for the backtest.

Finetuning the tokenizer matters most when your instrument's bar distribution is unlike the
pretraining mix (very illiquid names, unusual tick sizes, synthetic series).

## Troubleshooting

- **`ValueError: Input DataFrame contains NaN values`** — gaps in the price or volume
  columns of the input window. Drop or fill them; forward-fill is usually right for prices.
- **Flat or nonsensical forecast** — check the tokenizer matches the model, and that the
  input window has real variance in every column.
- **Forecast ignores an obvious trend** — expected. Normalization is per-window and there is
  no absolute time feature, so the model sees shape, not level or era.
- **OOM** — reduce `sample_count`, `pred_len`, or batch size; `max_context` bounds the
  attention window but each `sample_count` multiplies the effective batch.
- **Timestamps that don't exist** — extrapolating uniform steps past the last bar invents
  bars inside overnight and weekend gaps for intraday equity data. Supply real session
  timestamps as `y_timestamp` when that matters.
