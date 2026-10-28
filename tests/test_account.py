import unittest
from datetime import datetime, timedelta

from propfarm.account import FAILED, PASSED, FundedAccount
from propfarm.execution import ExecutionModel
from propfarm.farm import Farm
from propfarm.models import Bar, Side, Signal
from propfarm.risk import RiskConfig
from propfarm.rules import PropFirmRules
from propfarm.strategies import Strategy

T0 = datetime(2026, 3, 2, 10, 0)


class Scripted(Strategy):
    """Emits the signal queued for each bar index."""

    def __init__(self, signals):
        self.signals, self.i = signals, -1

    def on_bar(self, bar, position):
        self.i += 1
        return self.signals.get(self.i)


def bar(i, o, h, l, c, day=0):
    return Bar(T0 + timedelta(days=day, minutes=15 * i), o, h, l, c)


def rules(**kw):
    base = dict(firm="f", account_size=10_000, max_daily_loss=500, max_total_drawdown=1_000)
    base.update(kw)
    return PropFirmRules(**base)


def account(signals, risk=None, **rule_kw):
    return FundedAccount("a", "X", rules(**rule_kw), Scripted(signals), ExecutionModel(),
                         risk or RiskConfig(risk_per_trade=0.01, max_room_fraction=1.0, self_daily_stop=1.0))


class SizingTests(unittest.TestCase):
    def test_risk_per_trade_sets_quantity(self):
        a = account({})
        qty, risk = a.size(100, 99)  # 1% of 10k = 100 at risk, 1 point per unit
        self.assertEqual(qty, 100)
        self.assertAlmostEqual(risk, 100)

    def test_size_capped_by_room_to_floor(self):
        a = account({}, risk=RiskConfig(risk_per_trade=0.05, max_room_fraction=0.5))
        qty, _ = a.size(100, 99)  # room to daily floor 500 -> at most 250
        self.assertEqual(qty, 250)


class BracketTests(unittest.TestCase):
    def test_stop_assumed_before_target_in_same_bar(self):
        a = account({0: Signal(Side.LONG, stop=99, target=101)})
        a.on_bar(bar(0, 100, 100, 100, 100))
        a.on_bar(bar(1, 100, 102, 98, 100))
        self.assertEqual(a.trades[0].exit_reason, "stop")
        self.assertAlmostEqual(a.trades[0].pnl, -100)

    def test_gap_through_stop_fills_at_open(self):
        a = account({0: Signal(Side.LONG, stop=99, target=None)})
        a.on_bar(bar(0, 100, 100, 100, 100))
        a.on_bar(bar(1, 100, 100.5, 99.5, 100))
        a.on_bar(bar(2, 98, 98, 97, 97.5))
        self.assertAlmostEqual(a.trades[0].exit, 98)

    def test_skip_entry_when_open_gaps_past_stop(self):
        a = account({0: Signal(Side.LONG, stop=99, target=None)})
        a.on_bar(bar(0, 100, 100, 100, 100))
        a.on_bar(bar(1, 98, 98, 98, 98))
        self.assertIsNone(a.position)
        self.assertEqual(a.trades, [])


class RuleTests(unittest.TestCase):
    def test_gap_beyond_daily_limit_fails_account(self):
        a = account({0: Signal(Side.LONG, stop=99, target=None)})
        a.on_bar(bar(0, 100, 100, 100, 100))
        a.on_bar(bar(1, 100, 100, 100, 100))
        a.on_bar(bar(2, 90, 90, 90, 90))  # 100 units * 10 = -1000 > 500 daily limit
        self.assertEqual(a.status, FAILED)
        self.assertIn("daily", a.status_reason)

    def test_trailing_floor_follows_peak_and_locks(self):
        a = account({}, trailing_drawdown=True)
        a.peak = 10_500
        self.assertEqual(a.total_floor(), 9_500)
        a.peak = 12_000
        self.assertEqual(a.total_floor(), 10_000)

    def test_passes_after_target_and_min_days(self):
        a = account({0: Signal(Side.LONG, stop=99, target=106)}, profit_target=500, min_trading_days=1)
        a.on_bar(bar(0, 100, 100, 100, 100))
        a.on_bar(bar(1, 100, 100, 100, 100))
        a.on_bar(bar(2, 100, 107, 100, 106))
        self.assertEqual(a.status, PASSED)

    def test_consistency_rule_blocks_single_day_pass(self):
        a = account({0: Signal(Side.LONG, stop=99, target=106)}, profit_target=500,
                    consistency_max_day_fraction=0.5)
        a.on_bar(bar(0, 100, 100, 100, 100))
        a.on_bar(bar(1, 100, 100, 100, 100))
        a.on_bar(bar(2, 100, 107, 100, 106))
        self.assertNotEqual(a.status, PASSED)

    def test_self_daily_stop_halts_new_entries(self):
        sig = {0: Signal(Side.LONG, stop=99, target=None), 2: Signal(Side.LONG, stop=97, target=None)}
        a = account(sig, risk=RiskConfig(risk_per_trade=0.03, max_room_fraction=1.0, self_daily_stop=0.5))
        a.on_bar(bar(0, 100, 100, 100, 100))
        a.on_bar(bar(1, 100, 100, 100, 100))
        a.on_bar(bar(2, 100, 100, 98.9, 99))  # stopped out: -300 >= 50% of 500
        a.on_bar(bar(3, 99, 99, 99, 99))
        self.assertTrue(a.halted_today)
        self.assertIsNone(a.position)


class FarmTests(unittest.TestCase):
    def test_blocks_opposing_positions_at_same_firm(self):
        long_ = FundedAccount("long", "X", rules(), Scripted({0: Signal(Side.LONG, 99, None)}),
                              ExecutionModel(), RiskConfig())
        short = FundedAccount("short", "X", rules(), Scripted({0: Signal(Side.SHORT, 101, None)}),
                              ExecutionModel(), RiskConfig())
        farm = Farm([long_, short])
        farm.run({"X": [bar(0, 100, 100, 100, 100), bar(1, 100, 100, 100, 100)]})
        self.assertIsNotNone(long_.position)
        self.assertIsNone(short.position)
        self.assertEqual(farm.blocked_hedges, 1)


if __name__ == "__main__":
    unittest.main()
