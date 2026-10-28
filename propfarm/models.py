from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class Side(Enum):
    LONG = 1
    SHORT = -1


@dataclass(frozen=True)
class Bar:
    time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0


@dataclass
class Signal:
    """A strategy's request to open a position. Stops are mandatory."""

    side: Side
    stop: float
    target: float | None = None
    reason: str = ""


@dataclass
class Position:
    side: Side
    qty: float
    entry: float
    stop: float
    target: float | None
    opened: datetime
    reason: str = ""

    def unrealized(self, price: float, point_value: float) -> float:
        return (price - self.entry) * self.side.value * self.qty * point_value


@dataclass
class Trade:
    side: Side
    qty: float
    entry: float
    exit: float
    opened: datetime
    closed: datetime
    pnl: float
    risk: float
    exit_reason: str
    reason: str = ""

    @property
    def r_multiple(self) -> float:
        return self.pnl / self.risk if self.risk > 0 else 0.0


@dataclass
class EquityPoint:
    time: datetime
    equity: float


@dataclass
class AccountReport:
    name: str
    firm: str
    status: str
    status_reason: str
    start_balance: float
    balance: float
    trades: list[Trade] = field(default_factory=list)
    trading_days: int = 0
    max_drawdown: float = 0.0
    best_day: float = 0.0
