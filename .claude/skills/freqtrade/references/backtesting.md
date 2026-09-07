# Backtesting, hyperopt and analysis

Contents: [Data](#getting-data) · [Backtesting](#backtesting) · [Assumptions](#what-backtesting-assumes) · [Reading results](#reading-results) · [Hyperopt](#hyperopt) · [Overfitting](#overfitting) · [Validation commands](#validation-commands) · [Plotting](#plotting)

## Getting data

```bash
freqtrade download-data --exchange binance --pairs BTC/USDT ETH/USDT \
  --timeframes 5m 1h --timerange 20230101-
freqtrade download-data --exchange binance --pairs ".*/USDT" --days 90
freqtrade list-data --exchange binance          # what is already on disk
```

`--pairs` accepts regex. `--prepend` extends existing data backwards rather than refetching.
`--dl-trades` downloads raw trades and builds candles from them — needed on exchanges that
do not serve historic OHLCV (Kraken, notably), and much slower.

Download more than your test window: warm-up candles come out of the front of the range.
`--timeframes` must include every timeframe the strategy touches, informative pairs included.

Data lands in `user_data/data/<exchange>/` as feather by default (`--data-format-ohlcv`).

## Backtesting

```bash
freqtrade backtesting --strategy MyStrategy --timerange 20230101-20231231
freqtrade backtesting --strategy-list StratA StratB --timeframe 5m    # compare
freqtrade backtesting --strategy MyStrategy --timeframe-detail 5m     # 1h signals, 5m fills
freqtrade backtesting --strategy MyStrategy --breakdown month year
```

Useful flags: `--dry-run-wallet` (starting capital), `--fee` (override the exchange's),
`--max-open-trades`, `--enable-protections`, `--export trades|signals|none`,
`--backtest-directory`, `--cache none` (backtests are cached; this forces a re-run).

`--timeframe-detail` is the honesty check on entry timing: it replays a finer timeframe
inside each candle, so a strategy whose profit depends on where within the candle it filled
will show a different number. A large gap between the two is a warning.

## What backtesting assumes

Backtesting cannot see inside a candle, so it assumes:

- Entries fill at the candle's open, at the requested price, with no slippage, as long as
  the price falls within the candle's high/low.
- Exit signals fill at the **next** candle's open.
- Stoploss fills exactly at the stoploss price even if the low went lower — but costs
  `2 * fees` more than the nominal price.
- Within one candle the evaluation order is: exit signal, stoploss, ROI, trailing stop.
  Low is assumed to happen before high for stoploss purposes (capital protection first),
  and high before low for trailing-stop adjustment.
- ROI exits are capped at the ROI value even if the high went further, but are never below
  the candle.
- Exchange trading limits (min/max stake) are respected.

None of this models slippage on thin books, partial fills, exchange outages, or funding
rates on perpetuals. Every one of those costs money live and none appears in the backtest.
That gap is why dry-run is a required stage and not a formality.

## Reading results

The summary tables cover per-pair, per-tag (`enter_tag` / `exit_tag`), and periodic
breakdowns. What actually matters:

- **Trade count.** Under ~30 trades, every other statistic is noise. A 95% win rate over
  20 trades is not a finding.
- **Max drawdown**, not total profit — it is what determines whether the strategy is
  survivable at size.
- **Profit factor** (gross win / gross loss) and **expectancy** per trade.
- **Exit reason distribution.** A strategy whose profit comes entirely from `roi` exits with
  many `stop_loss` exits is being carried by the ROI table, not the entry logic.
- **Sharpe / Sortino / Calmar**, computed on daily wallet balance. Over short backtests with
  few trades these produce absurd values; treat them as comparative, not absolute.

Re-show a stored result without re-running: `freqtrade backtesting-show`. Deeper per-trade
analysis: `freqtrade backtesting-analysis` (needs `--export signals`).

Results are written to `user_data/backtest_results/` (zipped in recent versions — load them
with `freqtrade.data.btanalysis.load_backtest_stats` rather than parsing files by hand).

## Hyperopt

```bash
freqtrade hyperopt --strategy MyStrategy --hyperopt-loss SharpeHyperOptLossDaily \
  --spaces buy sell roi stoploss -e 500 --timerange 20230101-20230630 -j 4
freqtrade hyperopt-list --best --profitable
freqtrade hyperopt-show -n 3          # show epoch 3, then paste params into the strategy
```

Spaces: `buy`, `sell`, `roi`, `stoploss`, `trailing`, `protection`, `trades`, or `all`.
Only spaces you name are optimized; the rest keep their coded values.

Loss functions (`--hyperopt-loss`), each optimizing something different:

| Loss | Optimizes for |
| --- | --- |
| `ShortTradeDurHyperOptLoss` | Default. Profit with a bias toward short trades. |
| `OnlyProfitHyperOptLoss` | Raw profit, ignoring risk. Overfits readily. |
| `SharpeHyperOptLoss` / `SharpeHyperOptLossDaily` | Risk-adjusted return. |
| `SortinoHyperOptLoss` / `SortinoHyperOptLossDaily` | Like Sharpe but penalizes only downside. |
| `CalmarHyperOptLoss` | Return over max drawdown. |
| `MaxDrawDownHyperOptLoss`, `MaxDrawDownRelativeHyperOptLoss`, `MaxDrawDownPerPairHyperOptLoss` | Drawdown control. |
| `ProfitDrawDownHyperOptLoss` | Profit balanced against drawdown. |
| `MultiMetricHyperOptLoss` | Blend of several metrics. |

The loss function is the entire specification of what you are asking for. `OnlyProfit` will
happily hand you a strategy with a 90% drawdown.

## Overfitting

Hyperopt evaluates thousands of parameter sets against one fixed sample and returns the one
that fit it best — including its noise. Treat every result as suspect until it survives data
it was not optimized on:

1. Optimize on one period (`--timerange 20230101-20230630`).
2. Backtest the winning parameters on a later, untouched period.
3. If profit collapses out of sample, the parameters described that sample, not the market.

Fewer parameters and wider ranges overfit less than many parameters and narrow ones. A
strategy needing 15 tuned constants to be profitable is fitting history.

## Validation commands

```bash
freqtrade lookahead-analysis --strategy MyStrategy --timerange 20230101-20230630
freqtrade recursive-analysis --strategy MyStrategy --startup-candle 199 399 999
```

`scripts/validate_strategy.py` runs both plus the backtest and summarizes them.

Two gotchas that produce confusing errors:

- `lookahead-analysis` forces market orders, which requires
  `"entry_pricing"`/`"exit_pricing"` → `"price_side": "other"` in the config. Otherwise it
  aborts with a config error unrelated to your strategy. It also requires `--timerange`.
- `recursive-analysis` defaults to warm-up sizes including 1999, more candles than some
  exchanges serve, which aborts the run. Pass a smaller `--startup-candle` set.

## Plotting

Needs the plot extras (`pip install freqtrade[plot]`):

```bash
freqtrade plot-dataframe --strategy MyStrategy -p BTC/USDT --indicators1 ema20 --indicators2 rsi
freqtrade plot-profit --strategy MyStrategy -p BTC/USDT ETH/USDT
```

Output is interactive HTML in `user_data/plot/`. Plotting entries and exits over the price
is often faster at finding a logic bug than reading the summary tables.
