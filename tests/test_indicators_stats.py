import unittest

from propfarm.data import synthetic
from propfarm.indicators import EMA, RSI
from propfarm.rules import PRESETS
from propfarm.stats import monte_carlo


class IndicatorTests(unittest.TestCase):
    def test_ema_seeds_with_sma(self):
        e = EMA(3)
        for x in (1, 2, 3):
            e.update(x)
        self.assertAlmostEqual(e.value, 2.0)
        e.update(6)
        self.assertAlmostEqual(e.value, 4.0)

    def test_rsi_is_100_on_monotonic_rise(self):
        r = RSI(3)
        for x in range(10):
            r.update(x)
        self.assertEqual(r.value, 100.0)

    def test_synthetic_is_deterministic(self):
        self.assertEqual(synthetic(days=3, seed=1), synthetic(days=3, seed=1))


class MonteCarloTests(unittest.TestCase):
    def test_negative_edge_mostly_fails(self):
        res = monte_carlo([-1, -1, 1], PRESETS["example_forex_2step_100k"], 0.01, runs=500)
        self.assertGreater(res.fail_rate, 0.9)

    def test_positive_edge_mostly_passes(self):
        res = monte_carlo([2, 2, -1], PRESETS["example_forex_2step_100k"], 0.01, runs=500)
        self.assertGreater(res.pass_rate, 0.9)


if __name__ == "__main__":
    unittest.main()
