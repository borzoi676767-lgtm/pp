"""A simulated funded/evaluation account that enforces its firm's rules bar by bar."""
from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Callable

from .execution import ExecutionModel
from .models import AccountReport, Bar, EquityPoint, Position, Side, Signal, Trade
from .risk import RiskConfig
from .rules import PropFirmRules
from .strategies import Strategy

ACTIVE, PASSED, FAILED = "ACTIVE", "PASSED", "FAILED"

# (account, side) -> may this account open a position on that side?
EntryGuard = Callable[["FundedAccount", Side], bool]


class FundedAccount:
    def __init__(self, name: str, symbol: str, rules: PropFirmRules, strategy: Strategy,
                 execution: ExecutionModel, risk: RiskConfig):
        self.name, self.symbol = name, symbol
        self.rules, self.strategy, self.ex, self.risk = rules, strategy, execution, risk
        self.balance = rules.account_size
        self.peak = rules.account_size
        self.status, self.status_reason = ACTIVE, ""
        self.position: Position | None = None
        self.pending: Signal | None = None
        self.pending_exit = False
        self.day: date | None = None
        self.day_start_equity = self.balance
        self.halted_today = False
        self.trades_today = 0
        self.trades: list[Trade] = []
        self.day_pnl: dict[date, float] = defaultdict(float)
        self.trading_days: set[date] = set()
        self.curve: list[EquityPoint] = []
        self.max_drawdown = 0.0
        self._last_price: float | None = None

    # ----- rule floors -------------------------------------------------------
    def total_floor(self) -> float:
        r = self.rules
        if not r.trailing_drawdown:
            return r.account_size - r.max_total_drawdown
        floor = self.peak - r.max_total_drawdown
        return min(floor, r.account_size) if r.trailing_locks_at_start else floor

    def daily_floor(self) -> float:
        return self.day_start_equity - self.rules.max_daily_loss

    def floor(self) -> float:
        return max(self.total_floor(), self.daily_floor())

    def equity(self, price: float | None = None) -> float:
        price = self._last_price if price is None else price
        if self.position is None or price is None:
            return self.balance
        return self.balance + self.position.unrealized(price, self.ex.point_value)

    # ----- trading -----------------------------------------------------------
    def size(self, entry: float, stop: float) -> tuple[float, float]:
        """Return (qty, risk in currency) for a trade, or (0, 0) if it does not fit."""
        dist = abs(entry - stop)
        if dist <= 0:
            return 0.0, 0.0
        room = self.equity(entry) - self.floor()
        budget = min(self.rules.account_size * self.risk.risk_per_trade, room * self.risk.max_room_fraction)
        per_unit = dist * self.ex.point_value + 2 * self.ex.commission_per_unit
        qty = self.ex.round_qty(budget / per_unit) if budget > 0 else 0.0
        return qty, qty * per_unit

    def _open(self, sig: Signal, bar: Bar, guard: EntryGuard | None) -> None:
        price = self.ex.fill_price(bar.open, sig.side, opening=True)
        # Skip if the open already gapped through the stop.
        if (price - sig.stop) * sig.side.value <= 0:
            return
        if guard is not None and not guard(self, sig.side):
            return
        qty, _ = self.size(price, sig.stop)
        if qty <= 0:
            return
        self.balance -= self.ex.commission(qty)
        self.position = Position(sig.side, qty, price, sig.stop, sig.target, bar.time, sig.reason)
        self.trades_today += 1
        self.trading_days.add(bar.time.date())

    def _close(self, raw_price: float, bar: Bar, why: str) -> None:
        p = self.position
        assert p is not None
        price = self.ex.fill_price(raw_price, p.side, opening=False)
        gross = (price - p.entry) * p.side.value * p.qty * self.ex.point_value
        fee = self.ex.commission(p.qty)
        self.balance += gross - fee
        pnl = gross - 2 * fee  # entry commission was charged on open
        risk = abs(p.entry - p.stop) * p.qty * self.ex.point_value + 2 * fee
        self.trades.append(Trade(p.side, p.qty, p.entry, price, p.opened, bar.time, pnl, risk, why, p.reason))
        self.day_pnl[bar.time.date()] += pnl
        self.position = None

    def _check_brackets(self, bar: Bar) -> None:
        p = self.position
        if p is None:
            return
        if p.side is Side.LONG:
            if bar.low <= p.stop:  # assume the stop fills first when both are touched
                self._close(min(bar.open, p.stop), bar, "stop")
            elif p.target is not None and bar.high >= p.target:
                self._close(max(bar.open, p.target), bar, "target")
        else:
            if bar.high >= p.stop:
                self._close(max(bar.open, p.stop), bar, "stop")
            elif p.target is not None and bar.low <= p.target:
                self._close(min(bar.open, p.target), bar, "target")

    def _fail(self, why: str, bar: Bar) -> None:
        if self.position is not None:
            self._close(bar.close, bar, "breach")
        self.status, self.status_reason = FAILED, why
        self.pending, self.pending_exit = None, False

    def passed_conditions(self) -> bool:
        r = self.rules
        if r.profit_target is None or self.position is not None:
            return False
        profit = self.balance - r.account_size
        if profit < r.profit_target or len(self.trading_days) < r.min_trading_days:
            return False
        if r.consistency_max_day_fraction is not None:
            best = max(self.day_pnl.values(), default=0.0)
            if best > r.consistency_max_day_fraction * profit:
                return False
        return True

    # ----- main loop ---------------------------------------------------------
    def on_bar(self, bar: Bar, guard: EntryGuard | None = None) -> None:
        if self.status != ACTIVE:
            return
        d = bar.time.date()
        if d != self.day:
            self.day = d
            self.day_start_equity = self.equity()
            self.halted_today = False
            self.trades_today = 0

        # 1. Orders queued on the previous bar fill at this bar's open.
        if self.position is not None and self.pending_exit:
            self._close(bar.open, bar, "signal exit")
        self.pending_exit = False
        if self.pending is not None and self.position is None and not self.halted_today:
            self._open(self.pending, bar, guard)
        self.pending = None

        # 2. Resting stop / target orders.
        self._check_brackets(bar)

        # 3. Firm rules, evaluated against the worst price inside the bar.
        p = self.position
        if p is not None:
            best_px, worst_px = (bar.high, bar.low) if p.side is Side.LONG else (bar.low, bar.high)
            self.peak = max(self.peak, self.equity(best_px))
            worst = self.equity(worst_px)
        else:
            self.peak = max(self.peak, self.balance)
            worst = self.balance
        self._last_price = bar.close
        if worst <= self.daily_floor():
            return self._fail(f"daily loss limit hit on {d}", bar)
        if worst <= self.total_floor():
            return self._fail(f"max drawdown hit on {d}", bar)
        self.max_drawdown = max(self.max_drawdown, self.peak - worst)

        # 4. Our own, tighter limits.
        day_loss = self.day_start_equity - self.equity()
        if day_loss >= self.risk.self_daily_stop * self.rules.max_daily_loss:
            self.halted_today = True
            if self.position is not None:
                self._close(bar.close, bar, "self daily stop")
        if self.rules.flat_by_hour is not None and bar.time.hour >= self.rules.flat_by_hour:
            if self.position is not None:
                self._close(bar.close, bar, "end of session")
            self.halted_today = True

        # 5. Strategy decides what to do at the next open.
        sig = self.strategy.on_bar(bar, self.position)
        if self.position is not None:
            self.pending_exit = self.strategy.should_exit(bar, self.position)
        elif sig is not None and not self.halted_today and self.trades_today < self.risk.max_trades_per_day:
            self.pending = sig

        # 6. Evaluation passed?
        if self.passed_conditions():
            self.status, self.status_reason = PASSED, f"target reached on {d}"
            if not self.risk.stop_when_passed:
                self.status = ACTIVE
        self.curve.append(EquityPoint(bar.time, self.equity()))

    def report(self) -> AccountReport:
        return AccountReport(
            name=self.name, firm=self.rules.firm, status=self.status, status_reason=self.status_reason,
            start_balance=self.rules.account_size, balance=self.balance, trades=list(self.trades),
            trading_days=len(self.trading_days), max_drawdown=self.max_drawdown,
            best_day=max(self.day_pnl.values(), default=0.0),
        )
