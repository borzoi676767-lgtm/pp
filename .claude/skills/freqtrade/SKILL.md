---
name: freqtrade
description: Build, backtest, optimize and run crypto trading strategies with Freqtrade, the open-source Python trading bot (github.com/freqtrade/freqtrade). Use this whenever the user mentions freqtrade, a trading bot, or wants to write or debug a trading strategy — including "backtest this strategy", "why is my strategy losing money", "hyperopt my parameters", "add an RSI entry condition", "download OHLCV data for backtesting", "set up a trading bot on Binance/Kraken", "check my strategy for lookahead bias", "my backtest looks great but live is terrible", or when they show you a Python class subclassing IStrategy with populate_indicators / populate_entry_trend. Covers strategy authoring, backtesting, hyperopt, dry-run and live deployment.
---

# Freqtrade

Freqtrade is a crypto trading bot: you write a strategy class, backtest it on historical
candles, optimize its parameters, then run it against an exchange. The bot handles order
placement, position tracking, stoploss and reporting.

The thing to hold onto throughout: **a good backtest is weak evidence.** Most strategies
that look profitable in backtesting are exploiting a bug or overfitting the sample, and
freqtrade ships specific tools to catch both. The workflow below is ordered to surface those
failures before money is involved, which is why validation comes before optimization.

## Setup

```bash
python .claude/skills/freqtrade/scripts/setup_freqtrade.py
```

Creates a venv at `~/.freqtrade-venv`, installs freqtrade (Python 3.11+ required), and
initializes a `user_data/` directory. Activate with `source ~/.freqtrade-venv/bin/activate`,
or call `~/.freqtrade-venv/bin/freqtrade` directly. Pass `--hyperopt` to include the
optimization extras, `--userdir PATH` to put `user_data/` somewhere specific.

TA-Lib, the C library the indicator bindings wrap, normally installs from a prebuilt wheel
with no compiler involved. If it does fail, the script says so and points at the two working
alternatives — the repo's own `setup.sh -i`, or the Docker image. Don't hand-compile it.

## Workflow

**1. Scaffold.** `freqtrade new-config --config user_data/config.json` walks through
exchange, stake currency and dry-run interactively. `freqtrade new-strategy --strategy
MyStrategy` writes a template into `user_data/strategies/` (add `--template advanced` for
the full callback surface).

**2. Get data.** Backtesting needs candles on disk:

```bash
freqtrade download-data --exchange binance --pairs BTC/USDT ETH/USDT \
  --timeframes 5m 1h --timerange 20230101-
```

Download more history than you plan to test on. Indicators need warm-up candles
(`startup_candle_count`), and freqtrade silently trims the start of your timerange to
supply them — a 200-period EMA on 5m candles eats most of a week.

**3. Write the strategy.** Three methods carry it: `populate_indicators` adds columns,
`populate_entry_trend` sets `enter_long` (and `enter_short` if `can_short`),
`populate_exit_trend` sets `exit_long`. Everything is vectorized over the whole dataframe.
See `references/strategy.md` for the interface, hyperoptable parameters, callbacks, and the
mistakes that produce fake profits.

**4. Backtest.**

```bash
freqtrade backtesting --strategy MyStrategy --timerange 20230101-20231231 --timeframe 5m
```

**5. Validate before you believe it.** This is the step people skip:

```bash
python .claude/skills/freqtrade/scripts/validate_strategy.py --strategy MyStrategy \
  --timerange 20230101-20231231
```

It runs the backtest, then `lookahead-analysis` (re-runs on truncated data to detect a
strategy peeking at future candles) and `recursive-analysis` (varies the warm-up window to
find indicators whose values change depending on how much history they were fed), and
summarizes all three with a verdict. A lookahead hit means the backtest is fiction — fix it
before reading another metric. A drift hit means the indicator will behave differently live
than it did in backtest, even without an outright bug. Exit code is 0 when the checks pass,
1 when something is wrong, 2 when a check could not run.

It needs the freqtrade venv and re-execs itself into `~/.freqtrade-venv` automatically, so
you can call it with any python. Two flags matter in practice: `--timerange` is required
(lookahead-analysis refuses without one), and `--recursive-threshold` sets how much
indicator drift counts as a problem.

**6. Optimize, carefully.**

```bash
freqtrade hyperopt --strategy MyStrategy --hyperopt-loss SharpeHyperOptLossDaily \
  --spaces buy sell roi stoploss -e 300 --timerange 20230101-20230630
```

Hyperopt is the fastest way to overfit ever invented: it searches thousands of parameter
sets against one sample and hands you the one that fit the noise best. Optimize on one
period and confirm on a later untouched one; a result that only works on the optimization
window is not a result. `references/backtesting.md` covers loss functions and spaces.

**7. Dry-run, then live.** `freqtrade trade --strategy MyStrategy` with `"dry_run": true`
paper-trades against live prices. Run it for weeks, not hours — dry-run is the only stage
that exercises real order timing, slippage and exchange behavior, none of which backtesting
models. See `references/config.md` before going live.

## Live trading

Going live means the bot places real orders with real money and can lose it. Treat the
switch from `"dry_run": true` to `false` as a decision that belongs to the user: confirm
explicitly before flipping it, and don't set it as a side effect of some other change.

API keys belong in the config or environment, never in a strategy file, a commit, or a
message. If you spot keys in something about to be committed, say so and stop. When adding
exchange credentials, restrict them to trading — never withdrawal.

Nothing here is investment advice, and backtest results say little about future returns.
That's worth stating once when someone is clearly about to trade on it, then dropping.

## References

- `references/strategy.md` — IStrategy interface, indicators, hyperoptable parameters,
  callbacks, informative pairs, and the common mistakes that fabricate profit.
- `references/backtesting.md` — command flags, the assumptions backtesting makes about
  intra-candle behavior, hyperopt loss functions and spaces, result analysis, plotting.
- `references/config.md` — config keys, exchange and pairlist setup, dry-run vs live,
  order types, protections, the REST API and Telegram.
