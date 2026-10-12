#!/usr/bin/env python3
"""Offline tests for the paper desk's rules. No network: fills use --price.

Run: python3 .claude/skills/paper-desk/scripts/test_desk.py
"""
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import desk  # noqa: E402

CFG = {"cost_bps": 0, "min_rr": 1.5, "max_stop_pct": 25}


def run(d, *argv):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = desk.main(["--dir", d, *argv])
    text = buf.getvalue()
    try:
        return code, json.loads(text)
    except ValueError:
        return code, text


def opened(d, stop=0.9, target=1.3, price=1.0, **kw):
    args = ["open", "--asset", "TEST", "--stop", str(stop), "--target", str(target),
            "--scanner", "PASS", "--fomo", "APPROVE", "--sizer", "APPROVE",
            "--reason", "test", "--price", str(price), "--price-source", "test"]
    for k, v in kw.items():
        args += [f"--{k.replace('_', '-')}", str(v)]
    return run(d, *args)


class Sizing(unittest.TestCase):
    def test_one_percent_risk_without_costs(self):
        s = desk.size_long(1000, 1.0, 0.9, 1.3, 1.0, CFG)
        self.assertEqual(s["verdict"], "APPROVE")
        self.assertEqual(s["qty"], 100)
        self.assertEqual(s["risk_usd"], 10.0)
        self.assertEqual(s["rr"], 3.0)

    def test_costs_count_inside_the_one_percent(self):
        s = desk.size_long(1000, 1.0, 0.9, 1.3, 1.0, {**CFG, "cost_bps": 50})
        self.assertLessEqual(s["risk_usd"], 10.0)
        self.assertGreater(s["risk_usd"], 9.99)
        self.assertLess(s["rr"], 3.0)

    def test_tight_stop_is_capped_not_levered(self):
        s = desk.size_long(1000, 1.0, 0.999, 1.01, 1.0, CFG)
        self.assertTrue(s["capped_by_no_leverage"])
        self.assertLessEqual(s["notional_usd"], 1000)
        self.assertLess(s["risk_usd"], 10)

    def test_rejections(self):
        self.assertEqual(desk.size_long(1000, 1.0, 1.1, 1.3, 1, CFG)["verdict"], "REJECT")  # stop above
        self.assertEqual(desk.size_long(1000, 1.0, 0.9, 1.1, 1, CFG)["verdict"], "REJECT")  # rr 1.0
        self.assertEqual(desk.size_long(1000, 1.0, 0.7, 2.0, 1, CFG)["verdict"], "REJECT")  # 30% stop

    def test_bets_need_the_whole_range_past_the_price(self):
        ok = desk.size_bet(1000, "YES", 0.38, 0.40, 0.50, 0.60, "MEDIUM", 1, CFG)
        self.assertEqual(ok["verdict"], "APPROVE")
        self.assertEqual(ok["stake_usd"], 10.0)
        self.assertEqual(desk.size_bet(1000, "YES", 0.38, 0.40, 0.35, 0.60, "MEDIUM", 1, CFG)["verdict"],
                         "REJECT")
        no = desk.size_bet(1000, "NO", 0.60, 0.62, 0.40, 0.50, "HIGH", 1, CFG)
        self.assertEqual((no["verdict"], no["fill_price"]), ("APPROVE", 0.4))
        self.assertEqual(desk.size_bet(1000, "YES", 0.38, 0.40, 0.5, 0.6, "LOW", 1, CFG)["verdict"], "REJECT")


class Fills(unittest.TestCase):
    def bar(self, t, o, h, l, c):
        return {"t": t, "o": o, "h": h, "l": l, "c": c, "v": 0}

    def test_target_in_entry_bar_does_not_count_but_stop_does(self):
        bars = [self.bar(0, 1.0, 1.4, 0.95, 1.0)]
        self.assertIsNone(desk.first_exit(bars, 60, 30, 0.9, 1.3))
        bars = [self.bar(0, 1.0, 1.0, 0.85, 1.0)]
        self.assertEqual(desk.first_exit(bars, 60, 30, 0.9, 1.3)[1], "stop hit")

    def test_both_in_one_bar_is_a_stop(self):
        bars = [self.bar(0, 1, 1, 1, 1), self.bar(60, 1.0, 1.4, 0.8, 1.2)]
        self.assertEqual(desk.first_exit(bars, 60, 30, 0.9, 1.3)[:2], (0.9, "stop hit"))

    def test_gap_through_stop_fills_at_the_open(self):
        bars = [self.bar(0, 1, 1, 1, 1), self.bar(60, 0.8, 0.85, 0.7, 0.75)]
        self.assertEqual(desk.first_exit(bars, 60, 30, 0.9, 1.3)[0], 0.8)

    def test_target(self):
        bars = [self.bar(0, 1, 1, 1, 1), self.bar(60, 1.1, 1.35, 1.05, 1.3)]
        self.assertEqual(desk.first_exit(bars, 60, 30, 0.9, 1.3)[:2], (1.3, "target hit"))


class LedgerRules(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = self.tmp.name
        run(self.d, "init", "--balance", "1000", "--cost-bps", "0")

    def tearDown(self):
        self.tmp.cleanup()

    def test_missing_approval_is_blocked_and_logged(self):
        code, out = run(self.d, "open", "--asset", "TEST", "--stop", "0.9", "--target", "1.3",
                        "--scanner", "PASS", "--fomo", "BLOCK", "--sizer", "APPROVE",
                        "--reason", "x", "--price", "1", "--price-source", "test")
        self.assertEqual((code, out["status"]), (1, "TRADE BLOCKED"))
        self.assertEqual(desk.State(desk.Ledger(self.d).events).blocked[0]["stage"], "buyer")

    def test_one_position_at_a_time(self):
        self.assertEqual(opened(self.d)[0], 0)
        code, out = opened(self.d)
        self.assertEqual(code, 1)
        self.assertIn("one position at a time", out["reason"])

    def test_manual_price_needs_a_source(self):
        code, out = run(self.d, "open", "--asset", "TEST", "--stop", "0.9", "--target", "1.3",
                        "--scanner", "PASS", "--fomo", "APPROVE", "--sizer", "APPROVE",
                        "--reason", "x", "--price", "1")
        self.assertEqual(code, 2)
        self.assertIn("--price-source", out["error"])

    def test_never_increase_risk_after_a_loss(self):
        opened(self.d, risk_pct=0.5)
        run(self.d, "close", "--id", "T-0001", "--reason", "test", "--price", "0.9", "--price-source", "t")
        code, out = opened(self.d, risk_pct=1.0)
        self.assertEqual(code, 1)
        self.assertIn("never increase risk after a loss", out["reason"])
        self.assertEqual(opened(self.d, risk_pct=0.5)[0], 0)

    def test_loss_shrinks_dollar_risk(self):
        opened(self.d)
        run(self.d, "close", "--id", "T-0001", "--reason", "t", "--price", "0.9", "--price-source", "t")
        _, out = opened(self.d)
        self.assertEqual(out["MAX DOLLAR RISK"], 9.9)  # 1% of $990

    def test_stats(self):
        opened(self.d)
        run(self.d, "close", "--id", "T-0001", "--reason", "t", "--price", "1.3", "--price-source", "t")
        opened(self.d)
        run(self.d, "close", "--id", "T-0002", "--reason", "t", "--price", "0.9", "--price-source", "t")
        run(self.d, "note", "--ref", "T-0002", "--mistakes", "chased, stop too tight")
        _, out = run(self.d, "stats", "--book", "crypto", "--json")
        s = out["books"][0]
        self.assertEqual((s["wins"], s["losses"], s["win_rate_pct"]), (1, 1, 50.0))
        self.assertEqual(s["total_pnl"], 19.7)  # +30, then -1% of $1,030 = -10.30
        self.assertTrue(s["winners_bigger_than_losers"])
        self.assertEqual((s["biggest_win"][1], s["biggest_loss"][1]), ("T-0001", "T-0002"))
        self.assertEqual(dict(s["most_common_mistakes"]), {"chased": 1, "stop-too-tight": 1})
        self.assertIn("too few to judge", s["sample_warning"])

    def test_no_wins_means_no_biggest_win(self):
        opened(self.d)
        run(self.d, "close", "--id", "T-0001", "--reason", "t", "--price", "0.9", "--price-source", "t")
        _, out = run(self.d, "stats", "--book", "crypto", "--json")
        self.assertIsNone(out["books"][0]["biggest_win"])

    def test_editing_a_result_is_detected(self):
        opened(self.d)
        run(self.d, "close", "--id", "T-0001", "--reason", "t", "--price", "0.9", "--price-source", "t")
        path = Path(self.d) / "ledger.jsonl"
        lines = path.read_text().splitlines()
        lines[2] = lines[2].replace('"pnl":-10.0', '"pnl":10.0')
        path.write_text("\n".join(lines) + "\n")
        code, out = run(self.d, "verify")
        self.assertEqual(code, 1)
        self.assertIn("edited", out["problems"][0])

    def test_deleting_a_line_is_detected(self):
        opened(self.d)
        run(self.d, "close", "--id", "T-0001", "--reason", "t", "--price", "0.9", "--price-source", "t")
        run(self.d, "block", "--asset", "X", "--stage", "fomo", "--reason", "pumping")
        path = Path(self.d) / "ledger.jsonl"
        lines = path.read_text().splitlines()
        del lines[2]
        path.write_text("\n".join(lines) + "\n")
        self.assertEqual(run(self.d, "verify")[0], 1)

    def test_rules_cannot_change_mid_experiment(self):
        opened(self.d)
        code, out = run(self.d, "init", "--balance", "5000", "--force")
        self.assertEqual(code, 2)
        self.assertIn("can't change mid-experiment", out["error"])

    def test_export_has_the_guide_columns(self):
        opened(self.d)
        run(self.d, "block", "--asset", "PEPE", "--stage", "fomo", "--reason", "up 12% in 15m")
        _, out = run(self.d, "export")
        text = Path(out["wrote"]).read_text()
        self.assertIn("Date,Asset,Entry,Exit,Stop,Position size,P&L,Result,Setup,FOMO check,Notes", text)
        self.assertIn("BLOCKED", text)


if __name__ == "__main__":
    unittest.main(verbosity=1)
