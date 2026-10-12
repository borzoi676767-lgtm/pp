#!/usr/bin/env python3
"""Paper ledger and rule enforcement for the six-agent paper desk.

PAPER ONLY. Nothing in this file talks to a broker or a wallet.

Every event is one line in an append-only, hash-chained ledger
(paper-trading/ledger.jsonl). No command edits or deletes a line, and
`verify` (also run by `stats` and `status`) detects any edit made by hand,
so a losing trade can't quietly disappear.

Two books, each with its own paper balance, one-open-position limit and
stats, so prediction-market side bets can't contaminate the main experiment:
  crypto   long-only spot, priced from Coinbase or a DEX pool
  pm       prediction-market paper bets (Polymarket / Kalshi)

Commands:
  init      create the ledger: starting balances, assumed costs, min reward/risk
  status    balances, open positions, counts
  size      Sizer: crypto setup            -> APPROVE / REJECT
  open      Buyer: paper-buy at live price -> ticket or TRADE BLOCKED
  pm-size   Sizer: prediction-market bet   -> APPROVE / REJECT
  pm-open   Buyer: paper-bet at live price -> ticket or TRADE BLOCKED
  block     log a setup an agent rejected
  check     close positions whose stop/target was hit or whose market resolved
  close     close a position at the live price (discretionary exit)
  note      Logger: why it closed, mistakes, lesson
  stats     the 20-trade report
  export    trades.csv for Google Sheets / Excel
  verify    check the hash chain
"""
import argparse
import csv
import hashlib
import json
import math
import os
import statistics
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import market  # noqa: E402

MAX_RISK_PCT = 1.0  # fixed rule; not configurable
BOOKS = ("crypto", "pm")
DEFAULT_DIR = Path(__file__).resolve().parents[4] / "paper-trading"
JUDGE_AFTER = 50   # guide: 50-100 trades before drawing conclusions
REPORT_EVERY = 20  # guide: stats every 20 trades


class DeskError(Exception):
    pass


# --- ledger -----------------------------------------------------------------

def _digest(event):
    body = {k: v for k, v in event.items() if k != "hash"}
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


class Ledger:
    def __init__(self, directory):
        self.dir = Path(directory)
        self.path = self.dir / "ledger.jsonl"
        self.events = []
        if self.path.exists():
            for line in self.path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    self.events.append(json.loads(line))

    def append(self, event, **fields):
        e = {"seq": len(self.events) + 1, "ts": now_iso(), "event": event, **fields,
             "prev": self.events[-1]["hash"] if self.events else "0" * 64}
        e["hash"] = _digest(e)
        self.dir.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(e, separators=(",", ":")) + "\n")
        self.events.append(e)
        return e

    def verify(self):
        problems, prev = [], "0" * 64
        for i, e in enumerate(self.events, 1):
            if e.get("seq") != i:
                problems.append(f"line {i}: seq is {e.get('seq')} (a line was removed or reordered)")
            if e.get("prev") != prev:
                problems.append(f"line {i}: chain broken (the line before it was edited or removed)")
            if e.get("hash") != _digest(e):
                problems.append(f"line {i}: contents edited after it was written")
            prev = e.get("hash")
        return problems


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def ts_of(iso):
    return datetime.strptime(iso, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp()


class State:
    def __init__(self, events):
        if not events or events[0]["event"] != "INIT":
            raise DeskError("no ledger yet: run `desk.py init --balance 1000` first")
        self.cfg = events[0]["config"]
        self.trades, self.blocked, self.notes = {}, [], {}
        for e in events[1:]:
            kind = e["event"]
            if kind == "OPEN":
                self.trades[e["id"]] = {**e, "status": "OPEN"}
            elif kind == "CLOSE":
                t = self.trades[e["id"]]
                t.update(status="CLOSED", exit=e["exit"], pnl=e["pnl"], r=e["r"], result=e["result"],
                         closed_ts=e["ts"], close_reason=e["reason"], exit_source=e["price_source"],
                         close_seq=e["seq"])
            elif kind == "BLOCKED":
                self.blocked.append(e)
            elif kind == "NOTE":
                self.notes.setdefault(e["ref"], []).append(e)
        self.balances = {b: self.cfg["balances"][b] + sum(
            t["pnl"] for t in self.trades.values() if t["book"] == b and t["status"] == "CLOSED")
            for b in BOOKS}

    def open_in(self, book):
        return [t for t in self.trades.values() if t["book"] == book and t["status"] == "OPEN"]

    def closed_in(self, book):
        return sorted((t for t in self.trades.values() if t["book"] == book and t["status"] == "CLOSED"),
                      key=lambda t: t["close_seq"])

    def next_id(self, prefix):
        if prefix == "X":
            n = len(self.blocked)
        else:
            n = sum(1 for t in self.trades.values() if t["id"].startswith(prefix))
        return f"{prefix}-{n + 1:04d}"

    def risk_cap(self, book):
        """Never increase risk after a loss: after a losing trade, the next one may
        risk at most what the loser risked."""
        closed = self.closed_in(book)
        if closed and closed[-1]["pnl"] < 0:
            return min(MAX_RISK_PCT, closed[-1]["risk_pct"]), closed[-1]["id"]
        return MAX_RISK_PCT, None


# --- sizing (pure) ----------------------------------------------------------

def floor_sig(x, n=6):
    if x <= 0:
        return 0.0
    q = 10 ** (math.floor(math.log10(x)) - n + 1)
    return float(f"{math.floor(x / q + 1e-9) * q:.{n}g}")


def r2(x):
    return round(x, 2)


def size_long(balance, entry, stop, target, risk_pct, cfg):
    """Long-only sizing. Costs (fee + slippage per side) are inside both the risk
    and the reward, so '1% risk' means 1% actually lost if the stop fills."""
    out = {"book": "crypto", "balance": r2(balance), "entry": entry, "stop": stop,
           "target": target, "risk_pct": risk_pct}
    if not stop < entry < target:
        return {**out, "verdict": "REJECT", "reasons": ["long only: needs stop < entry < target"]}
    c = cfg["cost_bps"] / 1e4
    loss_per_unit = (entry - stop) + c * (entry + stop)
    gain_per_unit = (target - entry) - c * (entry + target)
    max_risk = balance * risk_pct / 100
    qty = max_risk / loss_per_unit
    capped = qty * entry * (1 + c) > balance
    if capped:  # never use leverage: the position can't cost more than the account
        qty = balance / (entry * (1 + c))
    qty = floor_sig(qty)
    stop_pct = (entry - stop) / entry * 100
    rr = gain_per_unit / loss_per_unit
    reasons = []
    if stop_pct > cfg["max_stop_pct"]:
        reasons.append(f"stop is {stop_pct:.1f}% below entry; max is {cfg['max_stop_pct']}%")
    if gain_per_unit <= 0:
        reasons.append("costs eat the whole move to target")
    elif rr < cfg["min_rr"]:
        reasons.append(f"reward/risk after costs is {rr:.2f}; minimum is {cfg['min_rr']}")
    if qty <= 0:
        reasons.append("position rounds to zero")
    out.update(max_risk_usd=r2(max_risk), stop_distance_pct=round(stop_pct, 2), qty=qty,
               notional_usd=r2(qty * entry), risk_usd=r2(qty * loss_per_unit),
               reward_usd=r2(qty * gain_per_unit), rr=round(rr, 2),
               capped_by_no_leverage=capped, cost_bps_per_side=cfg["cost_bps"],
               verdict="REJECT" if reasons else "APPROVE", reasons=reasons)
    return out


def size_bet(balance, side, yes_bid, yes_ask, est_low, est_high, confidence, risk_pct, cfg):
    """A contract bought at `price` pays 1 if right and 0 if wrong. Bet only when
    the whole estimated range sits on one side of the market price."""
    out = {"book": "pm", "balance": r2(balance), "side": side, "yes_bid": yes_bid, "yes_ask": yes_ask,
           "est_low": est_low, "est_high": est_high, "confidence": confidence, "risk_pct": risk_pct}
    reasons = []
    if not 0 <= est_low <= est_high <= 1:
        return {**out, "verdict": "REJECT", "reasons": ["estimates must satisfy 0 <= low <= high <= 1"]}
    if side == "YES":
        price = yes_ask
        if price is not None and not est_low > price:
            reasons.append(f"YES needs your LOW estimate ({est_low}) above the YES ask ({price})")
    else:
        price = round(1 - yes_bid, 4) if yes_bid is not None else None
        if yes_bid is not None and not est_high < yes_bid:
            reasons.append(f"NO needs your HIGH estimate ({est_high}) below the YES bid ({yes_bid})")
    if price is None or not 0 < price < 1:
        return {**out, "verdict": "REJECT", "reasons": ["no live price to fill at"]}
    if confidence == "LOW":
        reasons.append("confidence LOW: when reliable information is missing, SKIP")
    c = cfg["cost_bps"] / 1e4
    qty = floor_sig(balance * risk_pct / 100 / (1 + c) / price)
    stake = qty * price
    win = qty * (1 - price) - stake * c
    out.update(fill_price=price, qty=qty, stake_usd=r2(stake), risk_usd=r2(stake * (1 + c)),
               max_risk_usd=r2(balance * risk_pct / 100), reward_usd=r2(win),
               rr=round(win / (stake * (1 + c)), 2) if stake else None,
               cost_bps=cfg["cost_bps"], verdict="REJECT" if reasons else "APPROVE", reasons=reasons)
    return out


def first_exit(bars, gran, entry_ts, stop, target):
    """Walk bars after entry; the first stop or target touched closes the trade.
    Conservative on purpose, because paper fills flatter you:
      - a bar that touches both stop and target counts as the stop
      - a bar that opens below the stop fills at that open, not at the stop
      - in the bar containing the entry, a stop counts but a target does not
        (the high may have printed before you were in)
    """
    for c in bars:
        if c["t"] + gran <= entry_ts:
            continue
        entry_bar = c["t"] <= entry_ts
        if not entry_bar and c["o"] <= stop:
            return c["o"], "stop hit (gapped through)", c["t"]
        if c["l"] <= stop:
            return stop, "stop hit", c["t"]
        if not entry_bar and c["h"] >= target:
            return target, "target hit", c["t"]
    return None


def classify(pnl, risk):
    if pnl > 0.05 * risk:
        return "WIN"
    if pnl < -0.05 * risk:
        return "LOSS"
    return "BREAKEVEN"


# --- commands ---------------------------------------------------------------

def emit(obj):
    print(json.dumps(obj, indent=2))


def cmd_init(a, L):
    if L.events:
        trades = [e for e in L.events if e["event"] != "INIT"]
        if trades or not a.force:
            raise DeskError(
                f"ledger already exists with {len(L.events)} events. Rules can't change mid-experiment. "
                f"To start a NEW experiment, rename {L.path.name} (keep it: never delete losing history)."
                + ("" if trades else " Nothing is recorded yet, so --force will replace it."))
        L.path.unlink()
        L.events = []
    for name, v in (("--balance", a.balance), ("--pm-balance", a.pm_balance)):
        if v <= 0:
            raise DeskError(f"{name} must be positive")
    cfg = {"balances": {"crypto": a.balance, "pm": a.pm_balance}, "max_risk_pct": MAX_RISK_PCT,
           "cost_bps": a.cost_bps, "min_rr": a.min_rr, "max_stop_pct": a.max_stop_pct,
           "mode": "PAPER"}
    L.append("INIT", config=cfg)
    emit({"created": str(L.path), "config": cfg})


def cmd_size(a, L):
    st = State(L.events)
    cap, why = st.risk_cap("crypto")
    risk = a.risk_pct if a.risk_pct is not None else cap
    out = size_long(st.balances["crypto"], a.entry, a.stop, a.target, risk, st.cfg)
    _risk_rule(out, risk, cap, why)
    if st.open_in("crypto"):
        out["warning"] = f"{st.open_in('crypto')[0]['id']} is still open; the Buyer will block a second position"
    emit(out)
    return 0 if out["verdict"] == "APPROVE" else 1


def _risk_rule(out, risk, cap, why):
    if risk > cap:
        out["verdict"] = "REJECT"
        out.setdefault("reasons", []).append(
            f"never increase risk after a loss: {why} lost at {cap}% so the cap is {cap}%"
            if why else f"max risk per trade is {MAX_RISK_PCT}%")
    if risk <= 0:
        out["verdict"] = "REJECT"
        out.setdefault("reasons", []).append("risk must be positive")


def _chosen_risk(st, book, requested):
    cap, why = st.risk_cap(book)
    risk = requested if requested is not None else cap
    probe = {}
    _risk_rule(probe, risk, cap, why)
    return risk, "; ".join(probe.get("reasons", [])) or None


def _live_or_manual(a, symbol, side):
    """Fill at the live ask (buy) or bid (sell), or at a manual price that is
    labelled as such in the ledger."""
    if a.price is not None:
        if not a.price_source:
            raise DeskError("--price needs --price-source saying where the number came from")
        return a.price, f"manual: {a.price_source}"
    q = market.quote(symbol)
    if q["age_s"] is None or q["age_s"] > market.SCAN_LIMITS["max_quote_age_s"]:
        raise market.DataError(f"stale price for {symbol}: last print {q['age_s']}s ago")
    return (q["ask"] if side == "buy" else q["bid"]), q["source"]


def _block(L, st, book, asset, stage, reason, setup=""):
    e = L.append("BLOCKED", id=st.next_id("X"), book=book, asset=asset, stage=stage,
                 reason=reason, setup=setup)
    emit({"status": "TRADE BLOCKED", "reason": reason, "logged_as": e["id"]})
    return 1


def cmd_open(a, L):
    st = State(L.events)
    need = {"scanner": ("PASS", a.scanner), "fomo": ("APPROVE", a.fomo), "sizer": ("APPROVE", a.sizer)}
    bad = [f"{k}={(v or 'missing').upper()} (needs {want})" for k, (want, v) in need.items()
           if (v or "").upper() != want]
    if bad:
        return _block(L, st, "crypto", a.asset, "buyer", "missing approval: " + ", ".join(bad), a.setup)
    if st.open_in("crypto"):
        return _block(L, st, "crypto", a.asset, "buyer",
                      f"one position at a time: {st.open_in('crypto')[0]['id']} is still open", a.setup)
    if not a.reason.strip():
        return _block(L, st, "crypto", a.asset, "buyer", "every trade needs a written reason", a.setup)
    try:
        fill, source = _live_or_manual(a, a.asset, "buy")
    except market.DataError as e:
        return _block(L, st, "crypto", a.asset, "buyer", f"no live price: {e}", a.setup)
    risk, problem = _chosen_risk(st, "crypto", a.risk_pct)
    if problem:
        return _block(L, st, "crypto", a.asset, "buyer", problem, a.setup)
    s = size_long(st.balances["crypto"], fill, a.stop, a.target, risk, st.cfg)
    if s["verdict"] != "APPROVE":
        return _block(L, st, "crypto", a.asset, "buyer",
                      f"at the live price {fill}: " + "; ".join(s["reasons"]), a.setup)
    e = L.append("OPEN", id=st.next_id("T"), book="crypto", asset=a.asset, side="LONG",
                 entry=fill, stop=a.stop, target=a.target, qty=s["qty"], notional_usd=s["notional_usd"],
                 risk_usd=s["risk_usd"], risk_pct=risk, rr=s["rr"], balance_at_open=s["balance"],
                 cost_bps=st.cfg["cost_bps"], planned_entry=a.planned_entry,
                 slippage_vs_plan_pct=market.pct(fill, a.planned_entry) if a.planned_entry else None,
                 setup=a.setup, reason=a.reason, fomo_note=a.fomo_note,
                 approvals={"scanner": "PASS", "fomo": "APPROVE", "sizer": "APPROVE"}, price_source=source)
    emit({"PAPER TRADE ID": e["id"], "TOKEN": a.asset, "SIMULATED ENTRY": fill,
          "SIMULATED POSITION SIZE": f"{e['qty']} (${e['notional_usd']})", "STOP LOSS": a.stop,
          "TARGET": a.target, "MAX DOLLAR RISK": e["risk_usd"], "TIME ENTERED": e["ts"],
          "STATUS": "OPEN", "price_source": source, "reward_risk": e["rr"],
          "slippage_vs_plan_pct": e["slippage_vs_plan_pct"]})
    return 0


def cmd_pm_size(a, L):
    st = State(L.events)
    q = market.pm_quote(a.ref)
    cap, why = st.risk_cap("pm")
    risk = a.risk_pct if a.risk_pct is not None else cap
    out = size_bet(st.balances["pm"], a.side, q["yes_bid"], q["yes_ask"], a.est_low, a.est_high,
                   a.confidence, risk, st.cfg)
    _risk_rule(out, risk, cap, why)
    if q["closed"]:
        out["verdict"] = "REJECT"
        out["reasons"].append("market is closed")
    out["question"] = q["question"]
    emit(out)
    return 0 if out["verdict"] == "APPROVE" else 1


def cmd_pm_open(a, L):
    st = State(L.events)
    bad = []
    if (a.pm_verdict or "").upper() != a.side:
        bad.append(f"prediction-market agent said {(a.pm_verdict or 'missing').upper()}, bet is {a.side}")
    if (a.sizer or "").upper() != "APPROVE":
        bad.append(f"sizer={(a.sizer or 'missing').upper()} (needs APPROVE)")
    if bad:
        return _block(L, st, "pm", a.ref, "buyer", "missing approval: " + "; ".join(bad), a.setup)
    if st.open_in("pm"):
        return _block(L, st, "pm", a.ref, "buyer",
                      f"one position at a time: {st.open_in('pm')[0]['id']} is still open", a.setup)
    if not a.reason.strip():
        return _block(L, st, "pm", a.ref, "buyer", "every bet needs a written reason", a.setup)
    try:
        q = market.pm_quote(a.ref)
    except market.DataError as e:
        return _block(L, st, "pm", a.ref, "buyer", f"no live price: {e}", a.setup)
    risk, problem = _chosen_risk(st, "pm", a.risk_pct)
    if problem:
        return _block(L, st, "pm", a.ref, "buyer", problem, a.setup)
    s = size_bet(st.balances["pm"], a.side, q["yes_bid"], q["yes_ask"], a.est_low, a.est_high,
                 a.confidence, risk, st.cfg)
    if q["closed"]:
        s["verdict"], s["reasons"] = "REJECT", s["reasons"] + ["market is closed"]
    if s["verdict"] != "APPROVE":
        return _block(L, st, "pm", a.ref, "buyer", "at the live price: " + "; ".join(s["reasons"]), a.setup)
    e = L.append("OPEN", id=st.next_id("B"), book="pm", asset=a.ref, side=a.side,
                 question=q["question"], entry=s["fill_price"], stop=0.0, target=1.0, qty=s["qty"],
                 notional_usd=s["stake_usd"], risk_usd=s["risk_usd"], risk_pct=risk, rr=s["rr"],
                 balance_at_open=s["balance"], cost_bps=st.cfg["cost_bps"],
                 est_low=a.est_low, est_high=a.est_high, confidence=a.confidence,
                 setup=a.setup, reason=a.reason, closes=q["closes"],
                 approvals={"pm": a.side, "sizer": "APPROVE"}, price_source=q["venue"])
    emit({"PAPER BET ID": e["id"], "MARKET": q["question"], "SIDE": a.side,
          "SIMULATED FILL": s["fill_price"], "CONTRACTS": s["qty"], "STAKE": s["stake_usd"],
          "MAX DOLLAR RISK": s["risk_usd"], "PAYS IF RIGHT": r2(s["qty"]),
          "RESOLVES": q["closes"], "TIME ENTERED": e["ts"], "STATUS": "OPEN"})
    return 0


def cmd_block(a, L):
    st = State(L.events)
    if not a.reason.strip():
        raise DeskError("a blocked trade still needs the reason it was blocked")
    e = L.append("BLOCKED", id=st.next_id("X"), book=a.book, asset=a.asset, stage=a.stage,
                 reason=a.reason, setup=a.setup)
    emit({"logged": e["id"], "stage": a.stage, "asset": a.asset})


def _close(L, t, exit_price, reason, source, payout=False, **extra):
    c = t["cost_bps"] / 1e4
    exit_cost = 0.0 if payout else c * exit_price  # a resolved market settles; nothing is sold
    pnl = t["qty"] * (exit_price - t["entry"]) - t["qty"] * (c * t["entry"] + exit_cost)
    r = pnl / t["risk_usd"] if t["risk_usd"] else 0.0
    return L.append("CLOSE", id=t["id"], book=t["book"], asset=t["asset"], exit=exit_price,
                    pnl=r2(pnl), r=round(r, 2),
                    pnl_pct_position=round(pnl / t["notional_usd"] * 100, 2) if t["notional_usd"] else None,
                    pnl_pct_account=round(pnl / t["balance_at_open"] * 100, 3),
                    result=classify(pnl, t["risk_usd"]), reason=reason, price_source=source, **extra)


def _bar_size(span_s, max_bars):
    for g in market.GRANULARITIES:
        if span_s / g <= max_bars:
            return g
    return market.GRANULARITIES[-1]


def _bet_exit(t, q, sell):
    """Exit price for a bet, from the side that was bought."""
    if sell:
        return q["yes_bid"] if t["side"] == "YES" else (round(1 - q["yes_ask"], 4) if q["yes_ask"] else None)
    return q["yes_bid"] if t["side"] == "YES" else q["yes_ask"]


def cmd_check(a, L):
    st = State(L.events)
    report = []
    for t in sorted(st.trades.values(), key=lambda t: t["seq"]):
        if t["status"] != "OPEN":
            continue
        try:
            if t["book"] == "crypto":
                report.append(_check_crypto(L, t))
            else:
                report.append(_check_bet(L, t))
        except market.DataError as e:
            report.append({"id": t["id"], "status": "OPEN", "error": f"could not check: {e}"})
    emit({"checked": len(report), "positions": report})


def _check_crypto(L, t):
    now = time.time()
    entry_ts = ts_of(t["ts"])
    src = market.parse_symbol(t["asset"])[0]
    gran = _bar_size(now - entry_ts, 1500 if src == "coinbase" else 1000)
    bars = market.candles(t["asset"], gran, entry_ts - gran, now)
    hit = first_exit(bars, gran, entry_ts, t["stop"], t["target"])
    if hit:
        price, why, bar_t = hit
        e = _close(L, t, price, why, f"bars:{gran}s", bar_utc=datetime.fromtimestamp(
            bar_t, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
        return {"id": t["id"], "status": "CLOSED", "why": why, "exit": price, "pnl": e["pnl"],
                "r": e["r"], "result": e["result"]}
    q = market.quote(t["asset"])
    c = t["cost_bps"] / 1e4
    unreal = t["qty"] * (q["bid"] - t["entry"]) - t["qty"] * c * (t["entry"] + q["bid"])
    return {"id": t["id"], "status": "OPEN", "asset": t["asset"], "entry": t["entry"], "now": q["bid"],
            "stop": t["stop"], "target": t["target"], "unrealized_pnl": r2(unreal),
            "unrealized_r": round(unreal / t["risk_usd"], 2), "bars_checked": len(bars), "bar_s": gran}


def _check_bet(L, t):
    q = market.pm_quote(t["asset"])
    if q["result"]:
        won = q["result"] == t["side"]
        e = _close(L, t, 1.0 if won else 0.0, f"market resolved {q['result']}", q["venue"], payout=True)
        return {"id": t["id"], "status": "CLOSED", "why": f"resolved {q['result']}", "pnl": e["pnl"],
                "result": e["result"]}
    if q["closed"]:
        return {"id": t["id"], "status": "OPEN", "note": "market closed, awaiting resolution"}
    mark = _bet_exit(t, q, sell=True)
    unreal = t["qty"] * ((mark or 0) - t["entry"]) - t["qty"] * t["cost_bps"] / 1e4 * t["entry"]
    return {"id": t["id"], "status": "OPEN", "question": t.get("question"), "side": t["side"],
            "entry": t["entry"], "now_sell_price": mark, "unrealized_pnl": r2(unreal), "closes": q["closes"]}


def cmd_close(a, L):
    st = State(L.events)
    t = st.trades.get(a.id)
    if not t or t["status"] != "OPEN":
        raise DeskError(f"{a.id} is not an open position")
    if not a.reason.strip():
        raise DeskError("every exit needs a written reason")
    if a.price is not None:
        if not a.price_source:
            raise DeskError("--price needs --price-source saying where the number came from")
        price, source = a.price, f"manual: {a.price_source}"
    elif t["book"] == "crypto":
        price, source = _live_or_manual(a, t["asset"], "sell")
    else:
        price, source = _bet_exit(t, market.pm_quote(t["asset"]), sell=True), "live"
        if price is None:
            raise DeskError("no bid to sell into; wait for resolution or pass --price")
    e = _close(L, t, price, a.reason, source)
    emit({"closed": t["id"], "exit": price, "pnl": e["pnl"], "r": e["r"], "result": e["result"],
          "price_source": source})


def cmd_note(a, L):
    st = State(L.events)
    known = set(st.trades) | {b["id"] for b in st.blocked}
    if a.ref not in known:
        raise DeskError(f"no trade or blocked setup called {a.ref}")
    if not any([a.why_closed, a.mistakes, a.lesson, a.text]):
        raise DeskError("a note needs at least one of --why-closed, --mistakes, --lesson, --text")
    tags = sorted({m.strip().lower().replace(" ", "-") for m in (a.mistakes or "").split(",") if m.strip()})
    e = L.append("NOTE", ref=a.ref, why_closed=a.why_closed, mistakes=tags, lesson=a.lesson, text=a.text)
    emit({"noted": a.ref, "seq": e["seq"], "mistakes": tags})


def book_stats(st, book):
    closed = st.closed_in(book)
    pnls = [t["pnl"] for t in closed]
    wins = [t for t in closed if t["result"] == "WIN"]
    losses = [t for t in closed if t["result"] == "LOSS"]
    equity, peak, dd = st.cfg["balances"][book], st.cfg["balances"][book], 0.0
    for p in pnls:
        equity += p
        peak = max(peak, equity)
        dd = max(dd, (peak - equity) / peak * 100)
    ids = {t["id"] for t in st.trades.values() if t["book"] == book} | \
          {b["id"] for b in st.blocked if b["book"] == book}
    tags = Counter(m for ref, ns in st.notes.items() if ref in ids for n in ns for m in n["mistakes"]
                   if m != "none")
    start = st.cfg["balances"][book]
    return {
        "book": book, "starting_balance": start, "current_balance": r2(st.balances[book]),
        "total_pnl": r2(sum(pnls)), "return_pct": round(sum(pnls) / start * 100, 2),
        "closed_trades": len(closed), "open_trades": len(st.open_in(book)),
        "wins": len(wins), "losses": len(losses), "breakeven": len(closed) - len(wins) - len(losses),
        "win_rate_pct": round(len(wins) / len(closed) * 100, 1) if closed else None,
        "avg_win": r2(statistics.fmean(t["pnl"] for t in wins)) if wins else None,
        "avg_loss": r2(statistics.fmean(t["pnl"] for t in losses)) if losses else None,
        "winners_bigger_than_losers": (statistics.fmean(t["pnl"] for t in wins) >
                                       -statistics.fmean(t["pnl"] for t in losses)) if wins and losses else None,
        "expectancy_per_trade": r2(statistics.fmean(pnls)) if pnls else None,
        "avg_r": round(statistics.fmean(t["r"] for t in closed), 2) if closed else None,
        "biggest_win": max(((t["pnl"], t["id"]) for t in wins), default=None),
        "biggest_loss": min(((t["pnl"], t["id"]) for t in losses), default=None),
        "max_drawdown_pct": round(dd, 2),
        "blocked": len([b for b in st.blocked if b["book"] == book]),
        "blocked_by_stage": dict(Counter(b["stage"] for b in st.blocked if b["book"] == book)),
        "most_common_mistakes": tags.most_common(3),
        "manually_priced_fills": sum(1 for t in st.trades.values() if t["book"] == book and (
            t["price_source"].startswith("manual") or t.get("exit_source", "").startswith("manual"))),
        "sample_warning": (f"{len(closed)} closed trades is too few to judge; the plan is 50-100"
                           if len(closed) < JUDGE_AFTER else None),
    }


def cmd_stats(a, L):
    problems = L.verify()
    st = State(L.events)
    books = [a.book] if a.book else list(BOOKS)
    out = {"ledger_intact": not problems, "problems": problems,
           "books": [book_stats(st, b) for b in books]}
    if a.json:
        emit(out)
        return 0
    if problems:
        print("WARNING: LEDGER WAS EDITED. These results can't be trusted:")
        for p in problems:
            print("  " + p)
        print()
    for s in out["books"]:
        print(f"== {s['book'].upper()} BOOK (paper) ==")
        print(f"  Balance        ${s['starting_balance']:,.2f} -> ${s['current_balance']:,.2f}  "
              f"({s['return_pct']:+.2f}%, P&L ${s['total_pnl']:+,.2f})")
        print(f"  Trades         {s['closed_trades']} closed, {s['open_trades']} open, {s['blocked']} blocked "
              f"{s['blocked_by_stage'] or ''}")
        if s["closed_trades"]:
            print(f"  Wins/Losses    {s['wins']} / {s['losses']} / {s['breakeven']} breakeven  "
                  f"(win rate {s['win_rate_pct']}%)")
            print(f"  Avg win/loss   {_m(s['avg_win'])} / {_m(s['avg_loss'])}   "
                  f"winners bigger than losers: {_yn(s['winners_bigger_than_losers'])}")
            print(f"  Expectancy     {_m(s['expectancy_per_trade'])} per trade, {s['avg_r']}R average")
            print(f"  Biggest        win {_big(s['biggest_win'])}, loss {_big(s['biggest_loss'])}")
            print(f"  Max drawdown   {s['max_drawdown_pct']}%")
        print(f"  Top mistakes   {', '.join(f'{k} x{n}' for k, n in s['most_common_mistakes']) or 'none logged'}")
        if s["manually_priced_fills"]:
            print(f"  Manual prices  {s['manually_priced_fills']} fills were typed in, not fetched")
        if s["sample_warning"]:
            print(f"  NOTE           {s['sample_warning']}")
        print()
    return 0


def _m(x):
    return "n/a" if x is None else f"${x:+,.2f}"


def _big(pair):
    return "n/a" if not pair else f"{_m(pair[0])} ({pair[1]})"


def _yn(x):
    return "n/a" if x is None else ("yes" if x else "NO")


def cmd_status(a, L):
    st = State(L.events)
    problems = L.verify()
    if a.json:
        emit({"ledger": str(L.path), "intact": not problems, "config": st.cfg, "balances": st.balances,
              "open": [{k: t[k] for k in ("id", "book", "asset", "side", "entry", "stop", "target", "qty",
                                          "risk_usd", "ts")} for t in st.trades.values() if t["status"] == "OPEN"],
              "closed": {b: len(st.closed_in(b)) for b in BOOKS}, "blocked": len(st.blocked)})
        return 0
    print(f"Ledger  {L.path}  ({len(L.events)} events, {'intact' if not problems else 'EDITED - run verify'})")
    print(f"Rules   max risk {MAX_RISK_PCT}%/trade, min reward/risk {st.cfg['min_rr']}, max stop "
          f"{st.cfg['max_stop_pct']}%, assumed cost {st.cfg['cost_bps']} bps/side, one position per book, PAPER")
    for b in BOOKS:
        n = len(st.closed_in(b))
        cap, why = st.risk_cap(b)
        print(f"{b:<7} ${st.balances[b]:,.2f}  closed {n}  next report at {(n // REPORT_EVERY + 1) * REPORT_EVERY}"
              + (f"  risk capped at {cap}% after {why}" if why and cap < MAX_RISK_PCT else ""))
        for t in st.open_in(b):
            print(f"  OPEN {t['id']} {t['asset']} {t['side']} @ {t['entry']}  stop {t['stop']}  "
                  f"target {t['target']}  risk ${t['risk_usd']}  since {t['ts']}")
    print(f"blocked {len(st.blocked)}")
    return 0


def cmd_export(a, L):
    st = State(L.events)
    out = Path(a.out) if a.out else L.dir / "trades.csv"
    rows = []
    for t in sorted(st.trades.values(), key=lambda t: t["seq"]):
        notes = st.notes.get(t["id"], [])
        rows.append({
            "Date": t["ts"], "Asset": t["asset"], "Entry": t["entry"], "Exit": t.get("exit", ""),
            "Stop": t["stop"], "Position size": t["qty"], "P&L": t.get("pnl", ""),
            "Result": t.get("result", "OPEN"), "Setup": t.get("setup", ""),
            "FOMO check": t["approvals"].get("fomo", "n/a (bet)") + (f" - {t['fomo_note']}" if t.get("fomo_note") else ""),
            "Notes": _notes_text(notes, t.get("close_reason")),
            "Book": t["book"], "ID": t["id"], "Side": t["side"], "Target": t["target"],
            "Notional $": t["notional_usd"], "Risk $": t["risk_usd"], "R": t.get("r", ""),
            "Reason": t["reason"], "Entry price source": t["price_source"],
            "Exit price source": t.get("exit_source", "")})
    for b in st.blocked:
        rows.append({"Date": b["ts"], "Asset": b["asset"], "Result": "BLOCKED", "Setup": b.get("setup", ""),
                     "FOMO check": "BLOCK" if b["stage"] == "fomo" else "",
                     "Notes": f"blocked at {b['stage']}: {b['reason']}"
                              + (" | " + _notes_text(st.notes.get(b["id"], []), None) if st.notes.get(b["id"]) else ""),
                     "Book": b["book"], "ID": b["id"]})
    rows.sort(key=lambda r: r["Date"])
    cols = ["Date", "Asset", "Entry", "Exit", "Stop", "Position size", "P&L", "Result", "Setup", "FOMO check",
            "Notes", "Book", "ID", "Side", "Target", "Notional $", "Risk $", "R", "Reason",
            "Entry price source", "Exit price source"]
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        for b in BOOKS:  # the summary block the guide puts at the top of the sheet
            s = book_stats(st, b)
            w.writerow([f"{b} book (PAPER)", "Starting balance", s["starting_balance"],
                        "Current balance", s["current_balance"], "Total trades", s["closed_trades"],
                        "Win rate %", s["win_rate_pct"] if s["win_rate_pct"] is not None else "",
                        "Total P&L", s["total_pnl"],
                        "Biggest win", s["biggest_win"][0] if s["biggest_win"] else "",
                        "Biggest loss", s["biggest_loss"][0] if s["biggest_loss"] else ""])
        w.writerow([])
        dw = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        dw.writeheader()
        dw.writerows(rows)
    emit({"wrote": str(out), "rows": len(rows)})


def _notes_text(notes, close_reason):
    parts = [f"closed: {close_reason}"] if close_reason else []
    for n in notes:
        if n.get("why_closed"):
            parts.append(f"why: {n['why_closed']}")
        if n.get("mistakes"):
            parts.append("mistakes: " + ", ".join(n["mistakes"]))
        if n.get("lesson"):
            parts.append(f"lesson: {n['lesson']}")
        if n.get("text"):
            parts.append(n["text"])
    return " | ".join(parts)


def cmd_verify(a, L):
    problems = L.verify()
    emit({"ledger": str(L.path), "events": len(L.events), "intact": not problems, "problems": problems})
    return 1 if problems else 0


def build_parser():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", default=os.environ.get("PAPER_DESK_DIR", str(DEFAULT_DIR)),
                    help="ledger directory (default: <project>/paper-trading)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("init")
    p.add_argument("--balance", type=float, required=True, help="crypto book starting paper balance")
    p.add_argument("--pm-balance", type=float, help="prediction-market book (default: same as --balance)")
    p.add_argument("--cost-bps", type=float, default=50, help="assumed fee+slippage per side, bps (default 50)")
    p.add_argument("--min-rr", type=float, default=1.5, help="minimum reward/risk after costs (default 1.5)")
    p.add_argument("--max-stop-pct", type=float, default=25, help="widest stop allowed, %% (default 25)")
    p.add_argument("--force", action="store_true", help="replace a ledger that has no trades yet")

    p = sub.add_parser("status")
    p.add_argument("--json", action="store_true")

    p = sub.add_parser("size")
    p.add_argument("--entry", type=float, required=True)
    p.add_argument("--stop", type=float, required=True)
    p.add_argument("--target", type=float, required=True)
    p.add_argument("--risk-pct", type=float, help=f"default: the current cap ({MAX_RISK_PCT}%%, lower after a loss)")

    def fill_args(p):
        p.add_argument("--price", type=float, help="manual fill price (logged as manual)")
        p.add_argument("--price-source", help="where a manual price came from")

    p = sub.add_parser("open")
    p.add_argument("--asset", required=True, help="DOGE or dex:<network>:<pool>")
    p.add_argument("--stop", type=float, required=True)
    p.add_argument("--target", type=float, required=True)
    p.add_argument("--scanner", help="must be PASS")
    p.add_argument("--fomo", help="must be APPROVE")
    p.add_argument("--sizer", help="must be APPROVE")
    p.add_argument("--setup", default="")
    p.add_argument("--reason", required=True)
    p.add_argument("--fomo-note", default="")
    p.add_argument("--planned-entry", type=float)
    p.add_argument("--risk-pct", type=float, help="default: the current cap")
    fill_args(p)

    def bet_args(p):
        p.add_argument("--ref", required=True, help="polymarket:<slug> or kalshi:<TICKER>")
        p.add_argument("--side", required=True, type=str.upper, choices=["YES", "NO"])
        p.add_argument("--est-low", type=float, required=True, help="your low estimate of P(YES)")
        p.add_argument("--est-high", type=float, required=True, help="your high estimate of P(YES)")
        p.add_argument("--confidence", required=True, type=str.upper, choices=["LOW", "MEDIUM", "HIGH"])

    p = sub.add_parser("pm-size")
    bet_args(p)
    p.add_argument("--risk-pct", type=float)

    p = sub.add_parser("pm-open")
    bet_args(p)
    p.add_argument("--pm-verdict", help="the prediction-market agent's PAPER BET (must equal --side)")
    p.add_argument("--sizer", help="must be APPROVE")
    p.add_argument("--setup", default="")
    p.add_argument("--reason", required=True)
    p.add_argument("--risk-pct", type=float, help="default: the current cap")

    p = sub.add_parser("block")
    p.add_argument("--book", choices=BOOKS, default="crypto")
    p.add_argument("--asset", required=True)
    p.add_argument("--stage", required=True, choices=["scanner", "fomo", "sizer", "buyer", "pm"])
    p.add_argument("--reason", required=True)
    p.add_argument("--setup", default="")

    sub.add_parser("check")

    p = sub.add_parser("close")
    p.add_argument("--id", required=True)
    p.add_argument("--reason", required=True)
    fill_args(p)

    p = sub.add_parser("note")
    p.add_argument("--ref", required=True, help="trade, bet or blocked id (T-0001, B-0001, X-0001)")
    p.add_argument("--why-closed")
    p.add_argument("--mistakes", help="comma-separated tags, e.g. chased,stop-too-tight (or none)")
    p.add_argument("--lesson")
    p.add_argument("--text")

    p = sub.add_parser("stats")
    p.add_argument("--book", choices=BOOKS)
    p.add_argument("--json", action="store_true")

    p = sub.add_parser("export")
    p.add_argument("--out")

    sub.add_parser("verify")
    return ap


def main(argv=None):
    a = build_parser().parse_args(argv)
    if a.cmd == "init" and a.pm_balance is None:
        a.pm_balance = a.balance
    L = Ledger(a.dir)
    handler = globals()["cmd_" + a.cmd.replace("-", "_")]
    try:
        return handler(a, L) or 0
    except DeskError as e:
        emit({"error": str(e)})
        return 2
    except market.DataError as e:
        emit({"error": f"market data: {e}", "verdict": "REJECT: no data, no trade"})
        return 2


if __name__ == "__main__":
    sys.exit(main())
