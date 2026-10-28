"""Run many accounts at once, each with its own strategy and rules.

The farm refuses any entry that would hedge one account against another on
the same symbol at the same firm. Opposing positions across accounts (one
wins the evaluation while the other is written off) break the terms of
every major prop firm and lead to voided payouts and bans.
"""
from __future__ import annotations

import json
from pathlib import Path

from .account import ACTIVE, FundedAccount
from .data import load_csv
from .execution import ExecutionModel
from .models import Bar, Side
from .risk import RiskConfig
from .rules import resolve
from .strategies import build


class Farm:
    def __init__(self, accounts: list[FundedAccount]):
        names = [a.name for a in accounts]
        if len(set(names)) != len(names):
            raise ValueError("account names must be unique")
        self.accounts = accounts
        self.blocked_hedges = 0

    @classmethod
    def from_config(cls, cfg: dict) -> Farm:
        accounts = []
        for a in cfg["accounts"]:
            accounts.append(FundedAccount(
                name=a["name"],
                symbol=a["symbol"],
                rules=resolve(a["rules"]),
                strategy=build(a["strategy"]),
                execution=ExecutionModel(**a.get("execution", {})),
                risk=RiskConfig.from_dict(a.get("risk", {})),
            ))
        return cls(accounts)

    def no_cross_hedge(self, acct: FundedAccount, side: Side) -> bool:
        for other in self.accounts:
            if other is acct or other.position is None:
                continue
            if other.symbol == acct.symbol and other.rules.firm == acct.rules.firm and other.position.side is not side:
                self.blocked_hedges += 1
                return False
        return True

    def run(self, data: dict[str, list[Bar]]) -> None:
        missing = {a.symbol for a in self.accounts} - set(data)
        if missing:
            raise ValueError(f"no data for symbols: {sorted(missing)}")
        timeline = sorted(((b.time, sym, b) for sym, bars in data.items() for b in bars), key=lambda x: (x[0], x[1]))
        by_symbol: dict[str, list[FundedAccount]] = {}
        for a in self.accounts:
            by_symbol.setdefault(a.symbol, []).append(a)
        for _, sym, bar in timeline:
            for acct in by_symbol.get(sym, []):
                acct.on_bar(bar, self.no_cross_hedge)

    def active(self) -> list[FundedAccount]:
        return [a for a in self.accounts if a.status == ACTIVE]


def load_config(path: str | Path) -> dict:
    with open(path) as f:
        return json.load(f)


def load_data(cfg: dict, base: Path) -> dict[str, list[Bar]]:
    return {sym: load_csv(base / p) for sym, p in cfg.get("data", {}).items()}
