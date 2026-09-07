# Configuration, deployment and live trading

Contents: [Shape](#shape-of-a-config) · [Money](#money-settings) · [Exchange](#exchange) · [Pairlists](#pairlists) · [Order types](#order-types-and-pricing) · [Protections](#protections) · [Dry-run vs live](#dry-run-vs-live) · [Secrets](#api-keys-and-secrets) · [Control surfaces](#rest-api-telegram-and-webhooks) · [Running](#running-the-bot)

## Shape of a config

`freqtrade new-config --config user_data/config.json` generates one interactively and leaves
`dry_run` on. Multiple `-c` flags merge left to right, which is the clean way to keep secrets
separate: a committed `config.json` plus an ignored `config-private.json` holding keys.

Inspect the merged result without starting anything: `freqtrade show-config`.

## Money settings

| Key | Meaning |
| --- | --- |
| `stake_currency` | What you trade against, e.g. `"USDT"`. |
| `stake_amount` | Per-trade size, or `"unlimited"` to split the wallet across `max_open_trades`. |
| `max_open_trades` | Concurrent positions; `-1` for unlimited. |
| `tradable_balance_ratio` | Fraction of the wallet the bot may use (default 0.99). |
| `dry_run_wallet` | Simulated starting balance in dry-run. |
| `timeframe` | Overrides the strategy's, if set. |
| `trading_mode` | `spot`, `margin`, or `futures`. |
| `margin_mode` | `isolated` or `cross`, for futures. |

`stake_amount: "unlimited"` with a large `max_open_trades` fragments capital into positions
too small to clear exchange minimums, and those trades are silently skipped.

## Exchange

```json
"exchange": {
    "name": "binance",
    "key": "", "secret": "",
    "pair_whitelist": ["BTC/USDT", "ETH/USDT"],
    "pair_blacklist": ["BNB/.*"],
    "ccxt_config": {},
    "ccxt_async_config": {}
}
```

`freqtrade list-exchanges` shows what is supported; `list-markets` / `list-pairs` show what a
given exchange offers; `list-timeframes` shows its candle sizes. Anything ccxt supports will
mostly work, but only the officially supported exchanges are tested.

`ccxt_config` passes options straight through to ccxt — the escape hatch for proxies,
rate limits, and account-type quirks. Behind an HTTP proxy, `{"aiohttp_trust_env": true}`
makes ccxt honor the `HTTPS_PROXY` environment variable, which it otherwise ignores.

## Pairlists

A pipeline: a generator first, then filters.

```json
"pairlists": [
    {"method": "VolumePairList", "number_assets": 20, "sort_key": "quoteVolume",
     "refresh_period": 1800},
    {"method": "AgeFilter", "min_days_listed": 30},
    {"method": "PriceFilter", "low_price_ratio": 0.01},
    {"method": "SpreadFilter", "max_spread_ratio": 0.005},
    {"method": "VolatilityFilter", "lookback_days": 10}
]
```

Generators: `StaticPairList`, `VolumePairList`, `PercentChangePairList`, `MarketCapPairList`,
`ProducerPairList`, `RemotePairList`. Filters: `AgeFilter`, `DelistFilter`,
`FullTradesFilter`, `OffsetFilter`, `PairInformationFilter`, `PerformanceFilter`,
`PrecisionFilter`, `PriceFilter`, `ShuffleFilter`, `SpreadFilter`, `VolatilityFilter`,
`RangeStabilityFilter`, `CrossMarketPairList`.

Test the pipeline without trading: `freqtrade test-pairlist`.

Dynamic pairlists and backtesting do not mix: backtesting needs a fixed set of pairs with
data on disk, so it uses the whitelist. A strategy validated against `StaticPairList` and
then run live on `VolumePairList` is running on pairs it was never tested on.

## Order types and pricing

```json
"order_types": {
    "entry": "limit", "exit": "limit",
    "stoploss": "market", "stoploss_on_exchange": false
},
"entry_pricing": {"price_side": "same", "use_order_book": true, "order_book_top": 1},
"exit_pricing":  {"price_side": "same", "use_order_book": true, "order_book_top": 1}
```

`stoploss_on_exchange` places the stop with the exchange, so it survives the bot dying — a
meaningful safety difference, and worth enabling where the exchange supports it.

Market orders require `price_side: "other"`. This is also why `lookahead-analysis`, which
forces market orders, refuses to run against a config using `"same"`.

## Protections

Circuit breakers that halt trading after things go wrong:

```json
"protections": [
    {"method": "StoplossGuard", "lookback_period_candles": 24, "trade_limit": 4,
     "stop_duration_candles": 12, "only_per_pair": false},
    {"method": "CooldownPeriod", "stop_duration_candles": 2},
    {"method": "MaxDrawdown", "lookback_period_candles": 48, "trade_limit": 20,
     "max_allowed_drawdown": 0.2},
    {"method": "LowProfitPairs", "lookback_period_candles": 360, "trade_limit": 4,
     "required_profit": 0.02}
]
```

Backtesting ignores protections unless you pass `--enable-protections`, so a backtest run
without it is not testing the configuration you intend to deploy.

## Dry-run vs live

`"dry_run": true` simulates orders against live market data: real prices and real signal
timing, no real money. This is the only stage that exercises order timing, spread, exchange
latency and outages — none of which backtesting models.

Run it for weeks, and compare its trade log against a backtest over the same period. They
should broadly agree. If dry-run is materially worse, the backtest is optimistic and the
difference is what you would have paid to find out live.

`"dry_run": false` places real orders with real money. Flipping it is the user's decision,
not a step to take on their behalf while doing something else.

## API keys and secrets

Keys belong in a config file excluded from version control, or in environment variables
(`FREQTRADE__EXCHANGE__KEY`, `FREQTRADE__EXCHANGE__SECRET` — any config path maps to
`FREQTRADE__SECTION__KEY`). Never in a strategy file, a commit, or a chat message.

When creating exchange API keys, enable trading and disable withdrawal. Restrict by IP where
the exchange allows it. A leaked trade-only key costs you a bad trade; a leaked
withdrawal-enabled key costs you the account.

`user_data/` holds the trade database and any live config — check what is in it before
committing anything from that directory.

## REST API, Telegram and webhooks

```json
"api_server": {
    "enabled": true, "listen_ip_address": "127.0.0.1", "listen_port": 8080,
    "jwt_secret_key": "<random>", "username": "...", "password": "..."
}
```

Bind to `127.0.0.1` unless you have deliberately put authentication and TLS in front of it —
the API can start, stop and force-exit trades. `freqtrade install-ui` adds the web UI;
`freqtrade webserver` runs the UI and backtesting without trading.

Telegram (`"telegram": {"enabled": true, "token": ..., "chat_id": ...}`) gives `/status`,
`/profit`, `/forceexit`, `/stopentry`. Webhooks post trade events to an arbitrary URL.

## Running the bot

```bash
freqtrade trade --strategy MyStrategy --config user_data/config.json
freqtrade trade --strategy MyStrategy --dry-run          # force dry-run regardless of config
```

Deployment: `docker compose up -d` with the official image, or the provided
`freqtrade.service` systemd unit (there is a watchdog variant that restarts on hang).

State lives in an SQLite database (`tradesv3.sqlite`, `tradesv3.dryrun.sqlite` for dry-run).
Back it up before upgrades; `freqtrade convert-db` migrates between database URLs, and
`freqtrade show-trades` reads the trade history out of it.

Upgrades can change strategy interface behavior — `freqtrade strategy-updater` migrates
older strategies, and the repo's `docs/strategy_migration.md` explains what changed.
