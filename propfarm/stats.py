from __future__ import annotations

import random
import statistics
from dataclasses import dataclass

from .models import Trade
from .rules import PropFirmRules


@dataclass
class TradeStats:
    trades: int
    win_rate: float
    profit_factor: float
    expectancy_r: float
    avg_win: float
    avg_loss: float
    net: float

    def edge(self) -> bool:
        return self.trades >= 30 and self.expectancy_r > 0 and self.profit_factor > 1.1


def trade_stats(trades: list[Trade]) -> TradeStats:
    if not trades:
        return TradeStats(0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    wins = [t.pnl for t in trades if t.pnl > 0]
    losses = [t.pnl for t in trades if t.pnl <= 0]
    gross_loss = -sum(losses)
    return TradeStats(
        trades=len(trades),
        win_rate=len(wins) / len(trades),
        profit_factor=(sum(wins) / gross_loss) if gross_loss > 0 else float("inf"),
        expectancy_r=statistics.fmean(t.r_multiple for t in trades),
        avg_win=statistics.fmean(wins) if wins else 0.0,
        avg_loss=statistics.fmean(losses) if losses else 0.0,
        net=sum(t.pnl for t in trades),
    )


@dataclass
class MonteCarloResult:
    runs: int
    pass_rate: float
    fail_rate: float
    unresolved_rate: float
    median_trades_to_pass: float | None


def monte_carlo(r_multiples: list[float], rules: PropFirmRules, risk_per_trade: float,
                trades_per_day: int = 2, max_trades: int = 400, runs: int = 5000,
                seed: int = 1) -> MonteCarloResult:
    """Resample historical R-multiples to estimate the odds an evaluation passes or fails.

    Use it to choose `risk_per_trade`: past results are resampled, so this
    is only as good as the trade sample you feed it.
    """
    if not r_multiples:
        raise ValueError("need at least one trade")
    if rules.profit_target is None:
        raise ValueError("rules have no profit_target")
    rng = random.Random(seed)
    risk_amt = rules.account_size * risk_per_trade
    passes = fails = 0
    to_pass: list[int] = []
    for _ in range(runs):
        eq = peak = rules.account_size
        day_start = eq
        days = 0
        outcome = None
        for n in range(max_trades):
            if n % trades_per_day == 0:
                day_start = eq
                days += 1
            eq += rng.choice(r_multiples) * risk_amt
            if rules.trailing_drawdown:
                peak = max(peak, eq)
                floor = peak - rules.max_total_drawdown
                if rules.trailing_locks_at_start:
                    floor = min(floor, rules.account_size)
            else:
                floor = rules.account_size - rules.max_total_drawdown
            if eq <= floor or eq <= day_start - rules.max_daily_loss:
                outcome = "fail"
                break
            if eq - rules.account_size >= rules.profit_target and days >= rules.min_trading_days:
                outcome = "pass"
                to_pass.append(n + 1)
                break
        passes += outcome == "pass"
        fails += outcome == "fail"
    return MonteCarloResult(
        runs=runs,
        pass_rate=passes / runs,
        fail_rate=fails / runs,
        unresolved_rate=(runs - passes - fails) / runs,
        median_trades_to_pass=statistics.median(to_pass) if to_pass else None,
    )
