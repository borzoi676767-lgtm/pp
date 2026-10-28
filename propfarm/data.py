from __future__ import annotations

import csv
import math
import random
from datetime import datetime, timedelta
from pathlib import Path

from .models import Bar


def load_csv(path: str | Path) -> list[Bar]:
    """Read bars from a CSV with columns time,open,high,low,close[,volume]; time is ISO 8601."""
    bars = []
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            row = {k.strip().lower(): v for k, v in row.items()}
            bars.append(Bar(
                time=datetime.fromisoformat(row["time"]),
                open=float(row["open"]), high=float(row["high"]),
                low=float(row["low"]), close=float(row["close"]),
                volume=float(row.get("volume") or 0),
            ))
    bars.sort(key=lambda b: b.time)
    return bars


def save_csv(bars: list[Bar], path: str | Path) -> None:
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["time", "open", "high", "low", "close", "volume"])
        for b in bars:
            w.writerow([b.time.isoformat(), f"{b.open:.4f}", f"{b.high:.4f}", f"{b.low:.4f}", f"{b.close:.4f}", b.volume])


def synthetic(days: int = 120, bars_per_day: int = 28, start_price: float = 5000.0,
              daily_vol: float = 0.012, seed: int = 7, start: datetime | None = None) -> list[Bar]:
    """Random-walk bars with drifting trend regimes. For demos and tests only:
    results on synthetic data say nothing about real-market performance."""
    rng = random.Random(seed)
    t = start or datetime(2026, 1, 5, 9, 30)
    price = start_price
    sigma = daily_vol / math.sqrt(bars_per_day)
    drift = 0.0
    bars: list[Bar] = []
    day = 0
    while day < days:
        if t.weekday() >= 5:
            t += timedelta(days=1)
            continue
        if rng.random() < 0.1:
            drift = rng.gauss(0, sigma * 0.15)
        session = t.replace(hour=9, minute=30)
        for i in range(bars_per_day):
            o = price
            path = [o]
            for _ in range(4):
                path.append(path[-1] * math.exp(drift + rng.gauss(0, sigma / 2)))
            c = path[-1]
            bars.append(Bar(session + timedelta(minutes=15 * i), o, max(path), min(path), c, 1000))
            price = c
        day += 1
        t += timedelta(days=1)
    return bars
