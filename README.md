# propfarm

A simulator for running a "farm" of prop-firm accounts (evaluations and funded
accounts). Each account has its own strategy, and every account is held inside
its firm's rules.

**No code can promise winning trades.** Most prop-firm evaluations fail, and a
strategy that wins in a backtest can still lose live. This tool helps you
manage that risk. It:

- keeps every account inside its daily-loss, max-drawdown, trailing-drawdown,
  consistency and end-of-session rules,
- shows whether a strategy has an edge in your data (win rate, profit factor,
  expectancy in R),
- estimates each evaluation's odds of passing or failing at a given
  risk per trade (Monte Carlo), so you can choose a risk size *before* you pay
  for an evaluation.

Standard library only (Python 3.10+). No installation needed.

## Quick start

```bash
# Demo on random-walk data (results are luck, not evidence)
python3 -m propfarm run --config examples/farm.json --synthetic

# Your own data: CSV with time,open,high,low,close[,volume]
python3 -m propfarm run --config examples/farm.json \
    --data MES=data/mes_15m.csv --data EURUSD=data/eurusd_15m.csv --json report.json

# Pass/fail odds for one account at several risk sizes
python3 -m propfarm montecarlo --config examples/farm.json --data ... \
    --account fut-eval-brkout --risk 0.0025 0.005 0.01

python3 -m unittest discover -s tests -t .
```

## How an account is simulated

Each bar, in this order:

1. Orders the strategy queued on the previous bar fill at this bar's open,
   after slippage and commission. An entry is skipped if the open has already
   gapped past its stop.
2. Resting stop and target orders are checked. If one bar touches both, the
   stop is assumed to fill first, which is the conservative choice.
3. Firm rules are checked against the **worst price inside the bar**. The
   trailing-drawdown peak uses the best price inside the bar, which is also
   conservative. A breach fails the account.
4. Your own, tighter limits apply on top of the firm's:
   - a self-imposed daily stop,
   - a cap on trades per day,
   - flattening at the session cut-off.
5. The strategy sees the closed bar and may queue an entry or an exit.
6. The account passes once all of these hold: profit target reached, minimum
   trading days met, consistency rule met, and no open position.

Position size is the smaller of these two:

- `risk_per_trade × account size`,
- `max_room_fraction` × the room left before the nearest breach floor.

So a single stopped-out trade cannot end the account unless price gaps
through the stop.

## Configuration

See `examples/farm.json`. Each account sets:

| key         | meaning                                                              |
|-------------|----------------------------------------------------------------------|
| `rules`     | a preset name from `propfarm/rules.py`, or an inline rules object    |
| `symbol`    | which data series it trades                                          |
| `strategy`  | `ema_trend`, `rsi_reversion` or `breakout`, with `params`            |
| `execution` | `point_value`, `qty_step`, `max_qty`, `slippage`, `commission_per_unit` |
| `risk`      | `risk_per_trade`, `max_room_fraction`, `self_daily_stop`, `max_trades_per_day` |

The rule presets are representative examples, not any one firm's rules. Copy
your firm's current terms into an inline `rules` object. Firms change their
rules often.

To add a strategy, subclass `Strategy` in `propfarm/strategies.py`. It must
return a `Signal` that includes a stop. Then register it in `REGISTRY`.

## Staying within firm terms

The farm **blocks any entry that would hedge one account against another**,
that is, opposing positions on the same symbol at the same firm (the count is
in the report). That trick ("one account passes, the other is written off")
breaks every major firm's terms, and firms void payouts for it. Also check
your firm's rules on these before running several accounts:

- account limits,
- copy trading across accounts,
- trading through news,
- using bots or EAs.

## Going live

Live broker adapters are deliberately left out. A sensible path:

1. Backtest on several years of real data. Look for 100+ trades and an edge
   that holds across separate time periods.
2. Run `montecarlo` to choose a risk size with acceptable pass/fail odds.
3. Forward-test on a demo or paper account for weeks.
4. Implement `LiveBroker` (`propfarm/execution.py`) for your platform. Always
   send the stop together with the entry as a bracket order.
