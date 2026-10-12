#!/usr/bin/env python3
"""Keyless, read-only market data for the paper desk.

Nothing in this file can place an order. It reads public endpoints only:

  DOGE, PEPE, WIF, ...       Coinbase spot <SYMBOL>-USD (candles + order book)
  dex:<network>:<pool>       GeckoTerminal DEX pool (candles + pool reserve)
  polymarket:<slug>          Polymarket market
  kalshi:<TICKER>            Kalshi market

Commands (all print JSON):
  scan  SYMBOL               Scanner metrics: moves, liquidity, S/R, volatility
  fomo  SYMBOL [--entry P]   Anti-FOMO metrics and hard blocks
  quote SYMBOL               Current price
  find  NAME                 Resolve a token name to Coinbase / DEX symbols
  pm-quote REF               Prediction-market prices, rules, resolution
  pm-search TEXT             Search Polymarket for markets

Every threshold that can block or skip a trade is in SCAN_LIMITS or
FOMO_LIMITS below and is echoed in the output, so a verdict can always be
traced to a number.
"""
import argparse
import json
import statistics
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

COINBASE = "https://api.exchange.coinbase.com"
GECKO = "https://api.geckoterminal.com/api/v2"
POLYMARKET = "https://gamma-api.polymarket.com"
KALSHI = "https://api.elections.kalshi.com/trade-api/v2"
HEADERS = {"User-Agent": "paper-desk/1.0", "Accept": "application/json"}

# Shared by both sources; GeckoTerminal has no 6h bar, so neither do we.
GRANULARITIES = (60, 300, 900, 3600, 86400)
GECKO_TIMEFRAME = {60: ("minute", 1), 300: ("minute", 5), 900: ("minute", 15),
                   3600: ("hour", 1), 86400: ("day", 1)}

SCAN_LIMITS = {
    "min_volume_24h_usd": 250_000,   # below this, SKIP: too thin to trust the chart
    "min_cex_depth_2pct_usd": 25_000,  # bid or ask depth within 2% of mid
    "min_dex_reserve_usd": 100_000,  # pool liquidity
    "max_quote_age_s": 600,          # no fresh print in 10 min -> stale
}
FOMO_LIMITS = {
    "move_5m_pct": 5.0,       # up this much in 5 minutes -> chasing
    "move_15m_pct": 10.0,     # up this much in 15 minutes -> chasing
    "ext_atr_5m": 3.0,        # this many 5m ATRs above the 5m EMA20 -> extended
    "vol_spike_x": 5.0,       # last 5m volume vs median of prior 2h, while rising
    "green_body_x": 3.0,      # last 1m green body vs median 1m range
    "max_staleness_s": 180,   # last 1m bar older than this -> no live tape
}


class DataError(Exception):
    pass


def http_json(url, params=None, timeout=15):
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers=HEADERS)
    where = url.split("?")[0]
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < 2:
                time.sleep(2 * (attempt + 1))
                continue
            raise DataError(f"HTTP {e.code} from {where}") from None
        except (urllib.error.URLError, TimeoutError, ValueError) as e:
            if attempt < 2:
                time.sleep(1)
                continue
            raise DataError(f"{type(e).__name__} from {where}: {e}") from None


def parse_symbol(symbol):
    """Return ("coinbase", "DOGE-USD", None) or ("gecko", network, pool)."""
    if symbol.lower().startswith("dex:"):
        parts = symbol.split(":")
        if len(parts) != 3 or not parts[1] or not parts[2]:
            raise DataError("DEX symbols look like dex:<network>:<pool_address>; "
                            "run `market.py find <name>` to get one")
        return "gecko", parts[1].lower(), parts[2]
    base = symbol.upper()
    if base.endswith("-USD"):
        base = base[:-4]
    if not base.isalnum():
        raise DataError(f"not a ticker: {symbol!r}")
    return "coinbase", f"{base}-USD", None


def candles(symbol, gran, start=None, end=None):
    """Bars ascending by time: {t, o, h, l, c, v}, t = bar open (unix s), v in USD."""
    if gran not in GRANULARITIES:
        raise DataError(f"granularity must be one of {GRANULARITIES}")
    src, a, b = parse_symbol(symbol)
    end = int(end or time.time())
    start = int(start or end - 300 * gran)
    bars = {}
    if src == "coinbase":
        t = start
        while t < end:
            chunk_end = min(end, t + 299 * gran)
            try:
                rows = http_json(f"{COINBASE}/products/{a}/candles",
                                 {"granularity": gran, "start": t, "end": chunk_end})
            except DataError as e:
                if "HTTP 404" in str(e):
                    raise DataError(f"{a} is not listed on Coinbase; for DEX tokens "
                                    f"run `market.py find <name>`") from None
                raise
            if isinstance(rows, dict):
                raise DataError(f"coinbase: {rows.get('message', rows)}")
            for ts, lo, hi, op, cl, vol in rows:
                bars[ts] = {"t": ts, "o": op, "h": hi, "l": lo, "c": cl, "v": vol * cl}
            t = chunk_end
    else:
        tf, agg = GECKO_TIMEFRAME[gran]
        limit = min(1000, max(1, (end - start) // gran + 1))
        d = http_json(f"{GECKO}/networks/{a}/pools/{b}/ohlcv/{tf}",
                      {"aggregate": agg, "limit": limit,
                       "before_timestamp": end + gran, "currency": "usd"})
        for ts, op, hi, lo, cl, vol in d["data"]["attributes"]["ohlcv_list"]:
            if ts + gran > start:
                bars[ts] = {"t": ts, "o": op, "h": hi, "l": lo, "c": cl, "v": vol}
    return [bars[k] for k in sorted(bars)]


def quote(symbol):
    src, a, b = parse_symbol(symbol)
    if src == "coinbase":
        try:
            q = http_json(f"{COINBASE}/products/{a}/ticker")
        except DataError as e:
            if "HTTP 404" in str(e):
                raise DataError(f"{a} is not listed on Coinbase; for DEX tokens "
                                f"run `market.py find <name>`") from None
            raise
        ts = _parse_iso(q.get("time"))
        return {"symbol": symbol, "source": f"coinbase:{a}", "price": float(q["price"]),
                "bid": float(q["bid"]), "ask": float(q["ask"]),
                "age_s": round(time.time() - ts) if ts else None}
    pool = _gecko_pool(a, b)
    last = candles(symbol, 60, time.time() - 3600)
    age = round(time.time() - (last[-1]["t"] + 60)) if last else None
    price = float(pool["base_token_price_usd"])
    # A DEX pool has no bid/ask; the pool price is both.
    return {"symbol": symbol, "source": f"geckoterminal:{a}:{b}", "pool": pool["name"],
            "price": price, "bid": price, "ask": price, "age_s": age}


def _parse_iso(s):
    if not s:
        return None
    from datetime import datetime
    s = s.replace("Z", "+00:00")
    if "." in s:  # Coinbase sends nanoseconds; fromisoformat takes at most 6 digits
        head, frac = s.split(".", 1)
        digits = "".join(ch for ch in frac if ch.isdigit())
        s = f"{head}.{digits[:6]}{frac[len(digits):]}"
    return datetime.fromisoformat(s).timestamp()


def _gecko_pool(network, pool):
    return http_json(f"{GECKO}/networks/{network}/pools/{pool}")["data"]["attributes"]


# --- indicators -------------------------------------------------------------

def ema(values, n):
    k = 2 / (n + 1)
    e = values[0]
    for v in values[1:]:
        e = v * k + e * (1 - k)
    return e


def atr(bars, n=14):
    trs = [max(c["h"] - c["l"], abs(c["h"] - p["c"]), abs(c["l"] - p["c"]))
           for p, c in zip(bars, bars[1:])]
    return statistics.fmean(trs[-n:]) if trs else 0.0


def pct(a, b):
    return round((a / b - 1) * 100, 2) if b else None


def close_before(bars, gran, cutoff):
    """Close of the last bar that had finished by `cutoff`. Gap-safe for sparse DEX bars."""
    done = [c for c in bars if c["t"] + gran <= cutoff]
    return done[-1]["c"] if done else None


def pivots(bars, k=3):
    """Swing lows/highs: a bar whose low/high is the extreme of the k bars each side."""
    lows, highs = [], []
    for i in range(k, len(bars) - k):
        window = bars[i - k:i + k + 1]
        if bars[i]["l"] == min(c["l"] for c in window):
            lows.append(bars[i]["l"])
        if bars[i]["h"] == max(c["h"] for c in window):
            highs.append(bars[i]["h"])
    return lows, highs


def sig(x, n=6):
    return float(f"{x:.{n}g}") if isinstance(x, float) else x


# --- commands ---------------------------------------------------------------

def cmd_scan(symbol, cost_bps=50):
    now = time.time()
    q = quote(symbol)
    price = q["price"]
    h1 = candles(symbol, 3600, now - 120 * 3600, now)
    m15 = candles(symbol, 900, now - 96 * 900, now)
    if len(h1) < 30 or len(m15) < 30:
        return {"symbol": symbol, "hard_skip": [f"not enough history ({len(h1)} 1h bars, "
                                                 f"{len(m15)} 15m bars)"], "quote": q}
    day = [c for c in h1 if c["t"] + 3600 > now - 86400]
    vol_24h = sum(c["v"] for c in day)
    atr_1h = atr(h1)
    atr_15 = atr(m15)
    lows, highs = pivots(h1)
    support = max((x for x in lows if x < price), default=None)
    resistance = min((x for x in highs if x > price), default=None)
    ranges_24h = [(c["h"] - c["l"]) / c["l"] * 100 for c in day if c["l"]]
    atr_1h_pct = atr_1h / price * 100
    max_range = max(ranges_24h, default=0)
    regime = ("extreme" if atr_1h_pct > 5 or max_range > 15 else
              "elevated" if atr_1h_pct > 2.5 or max_range > 7 else "orderly")

    out = {
        "symbol": symbol, "source": q["source"], "price": sig(price),
        "moves_pct": {"1h": pct(price, close_before(h1, 3600, now - 3600)),
                      "4h": pct(price, close_before(h1, 3600, now - 4 * 3600)),
                      "24h": pct(price, close_before(h1, 3600, now - 86400)),
                      "5d": pct(price, h1[0]["o"])},
        "volume_24h_usd": round(vol_24h),
        "range_24h": {"low": sig(min(c["l"] for c in day)), "high": sig(max(c["h"] for c in day))},
        "volatility": {"atr_1h": sig(atr_1h), "atr_1h_pct": round(atr_1h_pct, 2),
                       "max_1h_range_pct_24h": round(max_range, 2), "regime": regime},
        "extension": {"ema20_15m": sig(ema([c["c"] for c in m15], 20)),
                      "atr_15m": sig(atr_15),
                      "atrs_above_ema20_15m": round((price - ema([c["c"] for c in m15], 20)) / atr_15, 2)
                      if atr_15 else None},
        "levels_5d_1h_pivots": {"nearest_support": sig(support), "nearest_resistance": sig(resistance),
                                "window_low": sig(min(c["l"] for c in h1)),
                                "window_high": sig(max(c["h"] for c in h1))},
        "quote_age_s": q["age_s"],
        "limits": SCAN_LIMITS,
    }
    # Data-derived starting points; the Scanner may widen or reject them. The stop
    # sits under structure AND at least one 1h ATR away: a stop inside an hour's
    # normal range gets taken out by noise. Reward/risk is quoted after costs
    # because that is what the Sizer judges, and on tight stops costs dominate.
    if support and resistance:
        stop = min(support - 0.25 * atr_1h, price - atr_1h)
        c = cost_bps / 1e4
        loss = (price - stop) + c * (price + stop)
        gain = (resistance - price) - c * (price + resistance)
        out["candidates"] = {"stop": sig(stop), "target": sig(resistance),
                             "stop_distance_pct": round((price - stop) / price * 100, 2),
                             "rr_before_costs": round((resistance - price) / (price - stop), 2),
                             "rr_after_costs": round(gain / loss, 2), "cost_bps_per_side": cost_bps}

    skip, warn = [], []
    if vol_24h < SCAN_LIMITS["min_volume_24h_usd"]:
        skip.append(f"24h volume ${vol_24h:,.0f} < ${SCAN_LIMITS['min_volume_24h_usd']:,}")
    if q["age_s"] is None or q["age_s"] > SCAN_LIMITS["max_quote_age_s"]:
        skip.append(f"stale price: last print {q['age_s']}s ago")
    src = parse_symbol(symbol)
    if src[0] == "coinbase":
        out["liquidity"] = _book_depth(src[1])
        thin = min(out["liquidity"]["bid_depth_2pct_usd"], out["liquidity"]["ask_depth_2pct_usd"])
        if thin < SCAN_LIMITS["min_cex_depth_2pct_usd"]:
            skip.append(f"order book within 2% of mid only ${thin:,.0f} on the thin side")
    else:
        pool = _gecko_pool(src[1], src[2])
        reserve = float(pool.get("reserve_in_usd") or 0)
        out["liquidity"] = {"pool": pool["name"], "reserve_usd": round(reserve),
                            "pool_created_at": pool.get("pool_created_at"),
                            "txns_h1": (pool.get("transactions") or {}).get("h1")}
        if reserve < SCAN_LIMITS["min_dex_reserve_usd"]:
            skip.append(f"pool reserve ${reserve:,.0f} < ${SCAN_LIMITS['min_dex_reserve_usd']:,}")
        created = _parse_iso(pool.get("pool_created_at"))
        if created and now - created < 7 * 86400:
            warn.append(f"pool is {(now - created) / 86400:.1f} days old")
    if resistance is None:
        warn.append("price is at/above every 5-day pivot high: no overhead level to target")
    if support is None:
        warn.append("no 5-day pivot low below price: no structural place for a stop")
    if regime == "extreme":
        warn.append("extreme volatility regime")
    out["hard_skip"] = skip
    out["warnings"] = warn
    return out


def _book_depth(product):
    book = http_json(f"{COINBASE}/products/{product}/book", {"level": 2})
    bids = [(float(p), float(s)) for p, s, _ in book["bids"]]
    asks = [(float(p), float(s)) for p, s, _ in book["asks"]]
    if not bids or not asks:
        raise DataError(f"{product}: empty order book")
    mid = (bids[0][0] + asks[0][0]) / 2
    return {"spread_bps": round((asks[0][0] - bids[0][0]) / mid * 1e4, 1),
            "bid_depth_2pct_usd": round(sum(p * s for p, s in bids if p >= mid * 0.98)),
            "ask_depth_2pct_usd": round(sum(p * s for p, s in asks if p <= mid * 1.02))}


def cmd_fomo(symbol, entry=None):
    now = time.time()
    q = quote(symbol)
    price = q["price"]
    m1 = candles(symbol, 60, now - 120 * 60, now)
    m5 = candles(symbol, 300, now - 60 * 300, now)
    blocks = []
    if len(m1) < 20 or len(m5) < 26:
        return {"symbol": symbol, "price": sig(price), "verdict": "BLOCK", "limits": FOMO_LIMITS,
                "hard_blocks": [f"not enough recent bars to define risk ({len(m1)} 1m, {len(m5)} 5m)"]}
    # The last trade print, not the last bar: Coinbase publishes bars a minute or two late.
    staleness = q["age_s"] if q["age_s"] is not None else round(now - (m1[-1]["t"] + 60))
    move_5 = pct(price, close_before(m1, 60, now - 5 * 60))
    move_15 = pct(price, close_before(m1, 60, now - 15 * 60))
    move_60 = pct(price, close_before(m1, 60, now - 60 * 60))

    done5 = [c for c in m5 if c["t"] + 300 <= now]
    prior = [c["v"] for c in done5[-25:-1]]
    base_vol = statistics.median(prior) if prior else 0
    vol_x = round(done5[-1]["v"] / base_vol, 2) if base_vol else None

    a5 = atr(m5)
    ema5 = ema([c["c"] for c in m5], 20)
    ext = round((price - ema5) / a5, 2) if a5 else None

    ranges = [c["h"] - c["l"] for c in m1[-61:-2]]
    med_range = statistics.median(ranges) if ranges else 0
    last_two = m1[-2:]
    green_bodies = [c["c"] - c["o"] for c in last_two if c["c"] > c["o"]]
    body_x = round(max(green_bodies) / med_range, 2) if green_bodies and med_range else 0.0

    recent = m5[-24:]
    low_2h, high_2h = min(c["l"] for c in recent), max(c["h"] for c in recent)

    L = FOMO_LIMITS
    if staleness > L["max_staleness_s"]:
        blocks.append(f"no trade printed for {staleness}s: no live tape to judge")
    if move_5 is not None and move_5 >= L["move_5m_pct"]:
        blocks.append(f"up {move_5}% in 5 minutes (limit {L['move_5m_pct']}%)")
    if move_15 is not None and move_15 >= L["move_15m_pct"]:
        blocks.append(f"up {move_15}% in 15 minutes (limit {L['move_15m_pct']}%)")
    if ext is not None and ext >= L["ext_atr_5m"]:
        blocks.append(f"{ext} ATRs above the 5m EMA20 (limit {L['ext_atr_5m']}): extended, no base")
    if vol_x is None:
        blocks.append("no volume baseline in the last 2h: too illiquid to judge")
    elif vol_x >= L["vol_spike_x"] and (move_15 or 0) > 0:
        blocks.append(f"volume {vol_x}x its 2h median while rising (limit {L['vol_spike_x']}x)")
    if body_x >= L["green_body_x"]:
        blocks.append(f"entry right after a green 1m candle {body_x}x the median range "
                      f"(limit {L['green_body_x']}x)")

    out = {
        "symbol": symbol, "source": q["source"], "price": sig(price),
        "moves_pct": {"5m": move_5, "15m": move_15, "60m": move_60},
        "volume_last_5m_vs_2h_median_x": vol_x,
        "atrs_above_ema20_5m": ext, "atr_5m": sig(a5),
        "last_green_1m_body_vs_median_range_x": body_x,
        "range_2h": {"low": sig(low_2h), "high": sig(high_2h),
                     "price_position_pct": round((price - low_2h) / (high_2h - low_2h) * 100, 1)
                     if high_2h > low_2h else None},
        "last_bar_age_s": staleness,
        "limits": L,
        "hard_blocks": blocks,
        "verdict": "BLOCK" if blocks else "NO_HARD_FLAGS",
    }
    if entry is not None:
        out["entry"] = {"proposed": entry, "vs_price_pct": pct(entry, price),
                        "atrs_above_2h_low": round((entry - low_2h) / a5, 2) if a5 else None}
    return out


def cmd_find(name):
    out = {"query": name, "coinbase": None, "dex_pools": []}
    if name.isalnum():
        try:
            q = quote(name)
            out["coinbase"] = {"symbol": name.upper(), "price": sig(q["price"])}
        except DataError:
            pass
    d = http_json(f"{GECKO}/search/pools", {"query": name})
    for p in d.get("data", [])[:8]:
        net, _, addr = p["id"].partition("_")
        at = p["attributes"]
        out["dex_pools"].append({
            "symbol": f"dex:{net}:{addr}", "name": at.get("name"),
            "reserve_usd": round(float(at.get("reserve_in_usd") or 0)),
            "volume_24h_usd": round(float((at.get("volume_usd") or {}).get("h24") or 0)),
            "base_price_usd": sig(float(at.get("base_token_price_usd") or 0))})
    out["note"] = ("Prefer the Coinbase symbol when there is one. For a DEX pool, the token "
                   "you want must be the FIRST name in the pair (e.g. 'BONK / SOL').")
    return out


def pm_quote(ref):
    venue, _, key = ref.partition(":")
    venue = venue.lower()
    if venue == "polymarket":
        rows = http_json(f"{POLYMARKET}/markets", {"slug": key})
        if not rows:
            raise DataError(f"no Polymarket market with slug {key!r}; use pm-search")
        m = rows[0]
        outcomes = json.loads(m.get("outcomes") or "[]")
        prices = [float(x) for x in json.loads(m.get("outcomePrices") or "[]")]
        if len(outcomes) != 2 or len(prices) != 2:
            raise DataError("only two-outcome markets are supported")
        result = None
        if m.get("closed") and max(prices) >= 0.99:
            result = "YES" if prices[0] >= 0.99 else "NO"
        return {"ref": ref, "venue": "polymarket", "question": m.get("question"),
                "yes_means": outcomes[0], "no_means": outcomes[1],
                "yes_bid": _f(m.get("bestBid")), "yes_ask": _f(m.get("bestAsk")),
                "last": _f(m.get("lastTradePrice")), "implied_yes": prices[0],
                "volume_24h_usd": round(float(m.get("volume24hr") or 0)),
                "liquidity_usd": round(float(m.get("liquidityNum") or 0)),
                "closes": m.get("endDate"), "closed": bool(m.get("closed")),
                "result": result, "rules": (m.get("description") or "")[:1500]}
    if venue == "kalshi":
        m = http_json(f"{KALSHI}/markets/{key}")["market"]
        bid, ask = _f(m.get("yes_bid_dollars")), _f(m.get("yes_ask_dollars"))
        res = (m.get("result") or "").lower()
        return {"ref": ref, "venue": "kalshi", "question": m.get("title"),
                "yes_means": m.get("yes_sub_title") or "Yes", "no_means": m.get("no_sub_title") or "No",
                "yes_bid": bid, "yes_ask": ask, "last": _f(m.get("last_price_dollars")),
                "implied_yes": round((bid + ask) / 2, 4) if bid and ask else _f(m.get("last_price_dollars")),
                "volume_24h_contracts": _f(m.get("volume_24h_fp")),
                "closes": m.get("close_time"), "closed": m.get("status") not in ("active", "open"),
                "result": res.upper() if res in ("yes", "no") else None,
                "rules": " ".join(filter(None, [m.get("rules_primary"), m.get("rules_secondary")]))[:1500]}
    raise DataError("prediction-market refs look like polymarket:<slug> or kalshi:<TICKER>")


def _f(x):
    try:
        return float(x) if x not in (None, "") else None
    except (TypeError, ValueError):
        return None


def cmd_pm_search(text):
    d = http_json(f"{POLYMARKET}/public-search", {"q": text, "limit_per_type": 6})
    out = []
    for ev in d.get("events", []):
        for m in ev.get("markets", [])[:6]:
            if m.get("closed"):
                continue
            prices = json.loads(m.get("outcomePrices") or "[]")
            out.append({"ref": f"polymarket:{m.get('slug')}", "question": m.get("question"),
                        "implied_yes": float(prices[0]) if prices else None,
                        "closes": m.get("endDate")})
    return {"query": text, "markets": out[:15],
            "note": "Kalshi has no text search here; pass kalshi:<TICKER> to pm-quote directly."}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sc = sub.add_parser("scan")
    sc.add_argument("symbol")
    sc.add_argument("--cost-bps", type=float, default=50,
                    help="assumed fee+slippage per side; match `desk.py status` (default 50)")
    f = sub.add_parser("fomo")
    f.add_argument("symbol")
    f.add_argument("--entry", type=float)
    sub.add_parser("quote").add_argument("symbol")
    sub.add_parser("find").add_argument("name")
    sub.add_parser("pm-quote").add_argument("ref")
    sub.add_parser("pm-search").add_argument("text")
    args = ap.parse_args(argv)
    try:
        if args.cmd == "scan":
            out = cmd_scan(args.symbol, args.cost_bps)
        elif args.cmd == "fomo":
            out = cmd_fomo(args.symbol, args.entry)
        elif args.cmd == "quote":
            out = quote(args.symbol)
        elif args.cmd == "find":
            out = cmd_find(args.name)
        elif args.cmd == "pm-quote":
            out = pm_quote(args.ref)
        else:
            out = cmd_pm_search(args.text)
    except DataError as e:
        print(json.dumps({"error": str(e), "verdict_if_this_was_a_check": "SKIP/BLOCK: no data"}))
        return 2
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
