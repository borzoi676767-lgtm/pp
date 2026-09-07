# Writing a freqtrade strategy

Contents: [Interface](#the-interface) · [Indicators](#indicators) · [Signals](#entry-and-exit-signals) · [Attributes](#class-attributes) · [Hyperoptable parameters](#hyperoptable-parameters) · [Informative pairs](#informative-pairs) · [Callbacks](#callbacks) · [Lookahead bias](#lookahead-bias-the-one-that-matters) · [Warm-up](#warm-up-and-startup_candle_count)

## The interface

A strategy is a class in `user_data/strategies/` subclassing `IStrategy`. Scaffold one with
`freqtrade new-strategy --strategy MyStrategy` (`--template advanced` includes every
callback). Three methods do the work, each receiving and returning the whole dataframe:

```python
class MyStrategy(IStrategy):
    INTERFACE_VERSION = 3

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (dataframe["rsi"] < 30) & (dataframe["volume"] > 0),
            ["enter_long", "enter_tag"]] = (1, "rsi_oversold")
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[dataframe["rsi"] > 70, ["exit_long", "exit_tag"]] = (1, "rsi_overbought")
        return dataframe
```

`metadata["pair"]` tells you which pair you are looking at. Everything is vectorized over
the full dataframe — you are writing pandas, not a per-tick loop, which is the source of
both the speed and the lookahead hazard below.

## Indicators

`talib.abstract as ta` and `technical.qtpylib` are the usual sources. Add columns in
`populate_indicators` only; computing them in the signal methods recomputes them per call
and makes `lookahead-analysis` harder to interpret.

Always include `dataframe["volume"] > 0` in entry conditions. Exchanges emit zero-volume
candles during outages, and without the guard a strategy will "trade" on them in backtest
where it could not have live.

## Entry and exit signals

Set `enter_long` / `exit_long`, and `enter_short` / `exit_short` when `can_short = True`
(futures only). `enter_tag` and `exit_tag` label why a trade fired, and become columns in
backtest output — worth setting from the start, since they turn "the strategy lost money"
into "this specific condition lost money".

**Colliding signals**: if `enter_long` and `exit_long` are both 1 on a candle, freqtrade
does nothing and drops the entry. Same for `enter_long` with `enter_short`. A strategy that
mysteriously takes fewer trades than its conditions suggest usually has colliding signals.

## Class attributes

| Attribute | Meaning |
| --- | --- |
| `timeframe` | Candle size, e.g. `"5m"`. |
| `minimal_roi` | Dict of minutes-held → profit target, e.g. `{"60": 0.01, "0": 0.04}`. Read as: take 4% immediately, but after 60 minutes accept 1%. `"<N>": -1` force-exits at N minutes. |
| `stoploss` | Negative fraction, e.g. `-0.10`. Mandatory. |
| `trailing_stop`, `trailing_stop_positive`, `trailing_stop_positive_offset` | Trailing stop configuration. |
| `startup_candle_count` | Candles of warm-up the indicators need. See below — this one is routinely wrong. |
| `process_only_new_candles` | Recompute only on candle close (default True). |
| `use_exit_signal` | Whether `exit_long` is honored at all. |
| `can_short` | Futures/margin only. |
| `order_types`, `order_time_in_force` | Market vs limit, GTC vs IOC. |

Config values override class attributes, which surprises people: a `stoploss` in
`config.json` silently wins over the one in the strategy.

## Hyperoptable parameters

Replace a constant with a Parameter and hyperopt can search it:

```python
buy_rsi = IntParameter(20, 40, default=30, space="buy")
buy_adx = DecimalParameter(20, 40, decimals=1, default=30.1, space="buy")
buy_trigger = CategoricalParameter(["bb_lower", "macd_cross"], default="bb_lower", space="buy")
use_stop_protection = BooleanParameter(default=True, space="protection")
```

Read them as `self.buy_rsi.value`. Spaces are `buy`, `sell`, `roi`, `stoploss`, `trailing`,
`protection`, `trades`. Results land in a `.json` next to the strategy and are loaded
automatically afterwards — so a strategy can behave differently than its source suggests if
a stale hyperopt result file is sitting there. Delete it to go back to the coded defaults.

`optimize=False` pins a parameter during hyperopt while keeping it as a named value.

## Informative pairs

To use a higher timeframe or another pair, never plain-`merge` it — the merge aligns on open
time and leaks the future. Use the helpers:

```python
@informative("1h")
def populate_indicators_1h(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
    dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
    return dataframe
# -> column "rsi_1h" on the base timeframe, correctly shifted
```

or `merge_informative_pair(dataframe, informative, self.timeframe, "1h", ffill=True)`.
Both handle the shift that keeps the 1h candle from being visible before it closed.

## Callbacks

Beyond the three populate methods, `IStrategy` exposes hooks that run per-trade with real
position state — `custom_stoploss`, `custom_exit`, `custom_roi`, `custom_entry_price`,
`custom_exit_price`, `custom_stake_amount`, `confirm_trade_entry`, `confirm_trade_exit`,
`adjust_trade_position` (DCA / partial exits), `adjust_entry_price`, `adjust_order_price`,
`leverage`, `order_filled`, `bot_start`, `bot_loop_start`.

Unlike the populate methods, callbacks receive a single point in time, so absolute indexing
like `dataframe.iloc[-1]` **is** safe there. That asymmetry is the single most useful thing
to remember about callbacks.

## Lookahead bias, the one that matters

Backtesting hands your code the entire dataframe at once. Anything that reaches forward in
that frame produces a beautiful backtest and loses money live. The patterns to avoid:

- `shift(-1)` or any negative shift — that is literally next candle's data.
- `.iloc[-1]` or absolute positions inside `populate_*` — that is the end of the whole
  dataset in backtest, but the current candle live. (Fine in callbacks.)
- Whole-column aggregates: `dataframe["volume"].mean()` includes future rows at every point.
  Use `dataframe["volume"].rolling(window).mean()`.
- `.resample("1h")` — labels on the left border, moving data backwards in time. Use
  `.resample("1h", label="right")`.
- `.merge()` to bring in a longer timeframe. Use the informative helpers above.

Run `scripts/validate_strategy.py` after any change to the indicator or signal logic. The
detectors are helpers, not proofs — they catch the common shapes, and a clean result does
not guarantee the strategy is honest. But a positive result is always a real bug.

## Warm-up and `startup_candle_count`

Set it to the longest lookback any indicator needs — a 200-period EMA needs at least 200,
and MACD or ADX need considerably more than their nominal period to converge. Freqtrade
trims that many candles off the front of your timerange to supply the warm-up, so an
understated count silently produces indicators computed on too little history, which then
differ between backtest and live.

`recursive-analysis` is the tool for this: it recomputes indicators with different warm-up
sizes and reports how much each one moves. In practice the stock template's
`startup_candle_count = 30` leaves ADX drifting tens of percent — raise the count until the
drift settles rather than guessing.
