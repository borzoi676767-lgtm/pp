# Rules and where they're enforced

The guide's fixed rules are enforced in code, so an agent can't talk its way past one. Every refusal is written to the ledger.

| Guide rule | Enforced by | How |
|---|---|---|
| Paper trading only | design | No broker or wallet code exists. The six agents' `tools:` lists contain no order tools. "Buying" appends a line to a file. |
| Maximum one open position | `desk.py open` / `pm-open` | Refused and logged BLOCKED while the book has an open trade. One position per book: crypto and prediction markets are separate experiments. |
| Risk ≤ 1% per trade | `desk.py size` / `open` | Quantity = 1% of the *current* paper balance ÷ (stop distance + costs). The constant `MAX_RISK_PCT = 1.0` isn't configurable. |
| Every trade has a stop | `desk.py open` | `--stop` is required and must sit below entry. Bets: the stake is the stop. |
| Never increase risk after a loss | `State.risk_cap` | After a losing trade, the next may risk at most the loser's %. Dollar risk also shrinks with the balance, automatically. |
| Never chase a pump | `market.py fomo` + `paper-anti-fomo` | Hard blocks (below) the agent can't override. Its default is cautious. It never sees the Scanner's pitch. |
| Never hide losing trades | the ledger | Append-only, and each line carries the hash of the line before. `verify` finds any edit or deletion, and `stats`/`status` flag it. No command edits or deletes. |
| Every trade needs a written reason | `desk.py open` | `--reason` is required and can't be blank. |
| Agents disagree → skip | `desk.py open` | Needs `PASS` + `APPROVE` + `APPROVE` verbatim, or the trade is blocked and logged. |
| Never recommend leverage | `size_long` | The position can't cost more than the account. A tight stop gets a capped size, not a loan. |
| Don't let AI invent market data | `market.py` | Every fill comes from a live quote. A typed-in price needs `--price-source`, is labelled `manual:` in the ledger, and is counted in `stats`. |
| Stats every 20 trades | `paper-logger` + `stats` | `status` shows the next milestone. Below 50 closed trades, the report says it's too few to judge. |

## What this build adds to the guide

These are my choices, not the guide's. The configurable ones are set at `init` and frozen once trading starts.

- **Costs inside the 1%** (`--cost-bps`, default 50 bps per side). The guide never mentions fees. Without them, "risk 1%" is fiction and tight-stop meme trades look profitable when they aren't. This is the most consequential setting: on a ~1% stop, 50 bps per side costs about 1R round trip.
- **Minimum reward/risk after costs** (`--min-rr`, default 1.5), which the Sizer rejects below.
- **Widest stop** (`--max-stop-pct`, default 25%).
- **Long only.** The guide's agent is a Buyer, and meme coins are hard to short.
- **Prediction-market bets need the whole estimated range past the price.** YES requires your low estimate above the YES ask. NO requires your high estimate below the YES bid. LOW confidence is rejected.
- **A separate paper balance for prediction markets**, so side bets don't move the crypto sizing.

## Scanner hard skips (`market.py` `SCAN_LIMITS`)

| Check | Skip when |
|---|---|
| 24h volume | below $250,000 |
| Order-book depth (Coinbase) | below $25,000 within 2% of mid, on either side |
| Pool reserve (DEX) | below $100,000 |
| Freshness | no trade printed in 10 minutes |

The Scanner's candidate stop sits under the nearest 5-day 1h pivot low, and at least one 1h ATR below price. A stop inside an hour's normal range is noise, not invalidation.

## Anti-FOMO hard blocks (`market.py` `FOMO_LIMITS`)

| Check | Block when |
|---|---|
| 5-minute move | up ≥ 5% |
| 15-minute move | up ≥ 10% |
| Extension | ≥ 3 ATRs (5m) above the 5m EMA20 |
| Volume | last 5m bar ≥ 5× its 2-hour median while price is rising, or no volume baseline at all |
| Candle | the last green 1m body ≥ 3× the median 1m range |
| Tape | no trade in 3 minutes |

These are starting thresholds, not tuned values. Decide on any change before an experiment starts: a threshold loosened after a missed pump is the "changing rules after every loss" mistake. If you change one, start a new ledger.

## Paper fills (`desk.py`)

Paper fills flatter you, so these lean the other way:

- **Entries** fill at the live **ask**, and exits at the live **bid**. A DEX pool has one price, so it's both.
- **Stops and targets** are detected by walking the price bars since entry. A stop hit at 3am while nobody was checking still counts.
- A bar that touches **both** stop and target counts as the **stop**.
- A bar that **opens below** the stop fills at that open, not at the stop.
- In the bar containing the entry, a stop counts but a target doesn't (its high may have printed before you were in).
- Bar size grows with time in the trade (1m up to 1d), so a trade checked days later is judged on coarser bars. That makes "both in one bar → stop" more likely: one more reason to check often.
- Bets settle at 1 or 0 on resolution, with no exit cost.

## Data sources

All keyless and read-only: Coinbase Exchange public API, GeckoTerminal, Polymarket Gamma API, Kalshi public API. If a source is down or a token isn't listed, the answer is SKIP/BLOCK. Nothing is estimated.
