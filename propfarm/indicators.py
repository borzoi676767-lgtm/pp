"""Incremental indicators: feed one bar at a time, read `.value` (None until warm)."""
from __future__ import annotations

from collections import deque

from .models import Bar


class EMA:
    def __init__(self, period: int):
        self.period = period
        self.k = 2.0 / (period + 1)
        self.value: float | None = None
        self._seed: list[float] = []

    def update(self, x: float) -> float | None:
        if self.value is None:
            self._seed.append(x)
            if len(self._seed) == self.period:
                self.value = sum(self._seed) / self.period
        else:
            self.value += self.k * (x - self.value)
        return self.value


class ATR:
    """Wilder's average true range."""

    def __init__(self, period: int = 14):
        self.period = period
        self.value: float | None = None
        self._prev_close: float | None = None
        self._seed: list[float] = []

    def update(self, bar: Bar) -> float | None:
        if self._prev_close is None:
            tr = bar.high - bar.low
        else:
            tr = max(bar.high - bar.low, abs(bar.high - self._prev_close), abs(bar.low - self._prev_close))
        self._prev_close = bar.close
        if self.value is None:
            self._seed.append(tr)
            if len(self._seed) == self.period:
                self.value = sum(self._seed) / self.period
        else:
            self.value = (self.value * (self.period - 1) + tr) / self.period
        return self.value


class RSI:
    """Wilder's relative strength index."""

    def __init__(self, period: int = 14):
        self.period = period
        self.value: float | None = None
        self._prev: float | None = None
        self._gains: list[float] = []
        self._losses: list[float] = []
        self._avg_gain = 0.0
        self._avg_loss = 0.0

    def update(self, x: float) -> float | None:
        if self._prev is None:
            self._prev = x
            return None
        change = x - self._prev
        self._prev = x
        gain, loss = max(change, 0.0), max(-change, 0.0)
        if self.value is None and len(self._gains) < self.period:
            self._gains.append(gain)
            self._losses.append(loss)
            if len(self._gains) < self.period:
                return None
            self._avg_gain = sum(self._gains) / self.period
            self._avg_loss = sum(self._losses) / self.period
        else:
            self._avg_gain = (self._avg_gain * (self.period - 1) + gain) / self.period
            self._avg_loss = (self._avg_loss * (self.period - 1) + loss) / self.period
        if self._avg_loss == 0:
            self.value = 100.0
        else:
            rs = self._avg_gain / self._avg_loss
            self.value = 100.0 - 100.0 / (1.0 + rs)
        return self.value


class Donchian:
    """Highest high / lowest low of the previous `period` bars (excludes current bar)."""

    def __init__(self, period: int = 20):
        self.period = period
        self._highs: deque[float] = deque(maxlen=period)
        self._lows: deque[float] = deque(maxlen=period)
        self.upper: float | None = None
        self.lower: float | None = None

    def update(self, bar: Bar) -> None:
        if len(self._highs) == self.period:
            self.upper = max(self._highs)
            self.lower = min(self._lows)
        self._highs.append(bar.high)
        self._lows.append(bar.low)
