"""Strategies emit entry Signals (with a mandatory stop) and may request exits.

These are standard, well-known rule sets. None of them is a guaranteed winner:
validate any of them on your own data with `propfarm backtest` and
`propfarm montecarlo` before trading real money.
"""
from __future__ import annotations

from .indicators import ATR, EMA, RSI, Donchian
from .models import Bar, Position, Side, Signal


class Strategy:
    name = "base"

    def on_bar(self, bar: Bar, position: Position | None) -> Signal | None:
        """Called on each closed bar. Return a Signal to enter at the next bar's open."""
        raise NotImplementedError

    def should_exit(self, bar: Bar, position: Position) -> bool:
        """Return True to exit the open position at the next bar's open."""
        return False


class EmaTrend(Strategy):
    """Trade in the direction of a fast/slow EMA cross, filtered by a long trend EMA."""

    name = "ema_trend"

    def __init__(self, fast: int = 20, slow: int = 50, trend: int = 200,
                 atr_period: int = 14, stop_atr: float = 2.0, reward_risk: float = 2.0):
        self.fast, self.slow, self.trend = EMA(fast), EMA(slow), EMA(trend)
        self.atr = ATR(atr_period)
        self.stop_atr, self.rr = stop_atr, reward_risk
        self._prev_diff: float | None = None

    def on_bar(self, bar, position):
        f, s, t = self.fast.update(bar.close), self.slow.update(bar.close), self.trend.update(bar.close)
        a = self.atr.update(bar)
        if None in (f, s, t, a):
            return None
        diff, prev = f - s, self._prev_diff
        self._prev_diff = diff
        if position is not None or prev is None:
            return None
        stop_dist = self.stop_atr * a
        if prev <= 0 < diff and bar.close > t:
            return Signal(Side.LONG, bar.close - stop_dist, bar.close + self.rr * stop_dist, "ema cross up")
        if prev >= 0 > diff and bar.close < t:
            return Signal(Side.SHORT, bar.close + stop_dist, bar.close - self.rr * stop_dist, "ema cross down")
        return None

    def should_exit(self, bar, position):
        if self._prev_diff is None:
            return False
        return (position.side is Side.LONG and self._prev_diff < 0) or \
               (position.side is Side.SHORT and self._prev_diff > 0)


class RsiReversion(Strategy):
    """Fade RSI extremes in the direction of the long-term trend."""

    name = "rsi_reversion"

    def __init__(self, period: int = 2, oversold: float = 10, overbought: float = 90,
                 trend: int = 200, atr_period: int = 14, stop_atr: float = 2.5, exit_rsi: float = 50):
        self.rsi, self.trend, self.atr = RSI(period), EMA(trend), ATR(atr_period)
        self.oversold, self.overbought, self.exit_rsi = oversold, overbought, exit_rsi
        self.stop_atr = stop_atr

    def on_bar(self, bar, position):
        r, t, a = self.rsi.update(bar.close), self.trend.update(bar.close), self.atr.update(bar)
        if position is not None or None in (r, t, a):
            return None
        if bar.close > t and r < self.oversold:
            return Signal(Side.LONG, bar.close - self.stop_atr * a, None, f"rsi {r:.0f} oversold")
        if bar.close < t and r > self.overbought:
            return Signal(Side.SHORT, bar.close + self.stop_atr * a, None, f"rsi {r:.0f} overbought")
        return None

    def should_exit(self, bar, position):
        r = self.rsi.value
        if r is None:
            return False
        return (position.side is Side.LONG and r > self.exit_rsi) or \
               (position.side is Side.SHORT and r < self.exit_rsi)


class Breakout(Strategy):
    """Donchian channel breakout with an ATR stop and fixed reward:risk target."""

    name = "breakout"

    def __init__(self, period: int = 20, atr_period: int = 14, stop_atr: float = 1.5, reward_risk: float = 2.5):
        self.channel, self.atr = Donchian(period), ATR(atr_period)
        self.stop_atr, self.rr = stop_atr, reward_risk

    def on_bar(self, bar, position):
        upper, lower = self.channel.upper, self.channel.lower
        self.channel.update(bar)
        a = self.atr.update(bar)
        if position is not None or None in (upper, lower, a):
            return None
        d = self.stop_atr * a
        if bar.close > upper:
            return Signal(Side.LONG, bar.close - d, bar.close + self.rr * d, "channel breakout up")
        if bar.close < lower:
            return Signal(Side.SHORT, bar.close + d, bar.close - self.rr * d, "channel breakout down")
        return None


REGISTRY: dict[str, type[Strategy]] = {cls.name: cls for cls in (EmaTrend, RsiReversion, Breakout)}


def build(spec: dict) -> Strategy:
    name = spec["name"]
    if name not in REGISTRY:
        raise KeyError(f"unknown strategy {name!r}; choose from {sorted(REGISTRY)}")
    return REGISTRY[name](**spec.get("params", {}))
