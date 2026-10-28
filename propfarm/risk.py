"""Per-account risk settings, applied on top of (and tighter than) the firm's rules."""
from __future__ import annotations

from dataclasses import dataclass, fields


@dataclass(frozen=True)
class RiskConfig:
    # Planned loss per trade if the stop is hit, as a fraction of account size.
    risk_per_trade: float = 0.005
    # Never risk more than this fraction of the room left before the nearest breach floor.
    max_room_fraction: float = 0.5
    # Stop trading for the day after losing this fraction of the firm's daily limit.
    self_daily_stop: float = 0.5
    max_trades_per_day: int = 3
    # In an evaluation, stop trading once the target and all pass conditions are met.
    stop_when_passed: bool = True

    @classmethod
    def from_dict(cls, d: dict) -> RiskConfig:
        allowed = {f.name for f in fields(cls)}
        unknown = set(d) - allowed
        if unknown:
            raise ValueError(f"unknown risk keys: {sorted(unknown)}")
        cfg = cls(**d)
        if not 0 < cfg.risk_per_trade <= 0.05:
            raise ValueError("risk_per_trade must be in (0, 0.05]")
        if not 0 < cfg.max_room_fraction <= 1:
            raise ValueError("max_room_fraction must be in (0, 1]")
        return cfg
