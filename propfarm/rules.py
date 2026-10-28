"""Prop-firm rule sets.

Every firm words its rules differently. Check your firm's current terms and
encode them here; the presets are representative examples, not any specific
firm's rules.
"""
from __future__ import annotations

from dataclasses import dataclass, fields


@dataclass(frozen=True)
class PropFirmRules:
    firm: str
    account_size: float
    # Max loss in one trading day, measured from the day's starting equity.
    max_daily_loss: float
    # Max loss overall. Static: from account_size. Trailing: from peak equity.
    max_total_drawdown: float
    trailing_drawdown: bool = False
    # Trailing floor stops moving once it reaches the starting balance (common on futures evals).
    trailing_locks_at_start: bool = True
    # Evaluation target; None for an already-funded account.
    profit_target: float | None = None
    min_trading_days: int = 0
    # Best single day may be at most this fraction of total profit (None = no rule).
    consistency_max_day_fraction: float | None = None
    # Flatten before this hour (exchange time) if the firm forbids holding overnight.
    flat_by_hour: int | None = None

    @classmethod
    def from_dict(cls, d: dict) -> PropFirmRules:
        allowed = {f.name for f in fields(cls)}
        unknown = set(d) - allowed
        if unknown:
            raise ValueError(f"unknown rule keys: {sorted(unknown)}")
        return cls(**d)


PRESETS: dict[str, PropFirmRules] = {
    "example_forex_2step_100k": PropFirmRules(
        firm="example_forex",
        account_size=100_000,
        max_daily_loss=5_000,
        max_total_drawdown=10_000,
        profit_target=10_000,
        min_trading_days=4,
    ),
    "example_forex_funded_100k": PropFirmRules(
        firm="example_forex",
        account_size=100_000,
        max_daily_loss=5_000,
        max_total_drawdown=10_000,
    ),
    "example_futures_eval_50k": PropFirmRules(
        firm="example_futures",
        account_size=50_000,
        max_daily_loss=1_100,
        max_total_drawdown=2_000,
        trailing_drawdown=True,
        profit_target=3_000,
        min_trading_days=5,
        consistency_max_day_fraction=0.5,
        flat_by_hour=16,
    ),
}


def resolve(spec: str | dict) -> PropFirmRules:
    if isinstance(spec, str):
        if spec not in PRESETS:
            raise KeyError(f"unknown rules preset {spec!r}; choose from {sorted(PRESETS)}")
        return PRESETS[spec]
    return PropFirmRules.from_dict(spec)
