"""Fill model for simulation, plus the interface a live broker adapter must implement."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from .models import Side


@dataclass(frozen=True)
class ExecutionModel:
    point_value: float = 1.0      # currency per 1.0 price move per unit
    qty_step: float = 1.0         # contracts: 1; forex lots in units: e.g. 1000
    max_qty: float = float("inf")
    slippage: float = 0.0         # price units lost on every fill
    commission_per_unit: float = 0.0  # per side

    def fill_price(self, price: float, side: Side, opening: bool) -> float:
        # Buying (opening a long or closing a short) fills higher; selling fills lower.
        buying = (side is Side.LONG) == opening
        return price + self.slippage if buying else price - self.slippage

    def round_qty(self, qty: float) -> float:
        qty = min(qty, self.max_qty)
        return int(qty / self.qty_step) * self.qty_step

    def commission(self, qty: float) -> float:
        return qty * self.commission_per_unit


class LiveBroker(ABC):
    """Implement this against your platform's API (e.g. MT5, Rithmic, Tradovate, cTrader).

    Not included here on purpose: run the farm in simulation and paper-trade until
    the results hold up, then write and test an adapter against a demo account.
    Always send the stop to the broker as a resting order with the entry, so a
    crash or disconnect cannot leave a position unprotected.
    """

    @abstractmethod
    def equity(self) -> float: ...

    @abstractmethod
    def open_bracket(self, symbol: str, side: Side, qty: float, stop: float, target: float | None) -> str: ...

    @abstractmethod
    def close_all(self, symbol: str) -> None: ...
