from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import benchmarks as bm  # noqa: E402
import tca_decompose as td  # noqa: E402


class BenchmarkRegressionTests(unittest.TestCase):
    def setUp(self):
        self.rows = [
            {
                "datetime": "2026-07-24 09:29:00", "date": "20260724",
                "open": 100.0, "high": 100.0, "low": 100.0, "close": 100.0,
                "volume": 100.0, "amount": 10_000.0,
            },
            {
                "datetime": "2026-07-24 09:30:00", "date": "20260724",
                "open": 101.0, "high": 101.0, "low": 101.0, "close": 101.0,
                "volume": 100.0, "amount": 10_100.0,
            },
            {
                "datetime": "2026-07-24 09:31:00", "date": "20260724",
                "open": 110.0, "high": 110.0, "low": 110.0, "close": 110.0,
                "volume": 800.0, "amount": 88_000.0,
            },
        ]
        self.bars = bm.MinuteBars(self.rows)
        self.fill = {
            "symbol": "600000.SH",
            "side": "buy",
            "datetime": "2026-07-24 09:31:00",
            "price": 108.0,
            "qty": 1_000,
        }

    def decompose(self, benchmark):
        return td.decompose_fill(
            self.fill,
            self.bars,
            benchmark=benchmark,
            commission_bps=0.0,
            impact_coef=0.0,
        )

    def test_selected_benchmark_drives_timing_and_slippage(self):
        arrival = bm.arrival_price(
            self.bars, bm.parse_dt(self.fill["datetime"])
        )
        segment = self.bars.slice(
            bm.parse_dt("2026-07-24 09:16:00"),
            bm.parse_dt("2026-07-24 09:46:00"),
        )
        expected_benchmarks = {
            "vwap": bm.interval_vwap(segment),
            "twap": bm.interval_twap(segment),
            "arrival": arrival,
        }

        results = {name: self.decompose(name) for name in expected_benchmarks}
        for name, result in results.items():
            bench = expected_benchmarks[name]
            expected_timing = (
                0.0 if name == "arrival"
                else round((bench - arrival) / arrival * 10_000, 2)
            )
            expected_slippage = round(
                (self.fill["price"] - bench) / bench * 10_000, 2
            )
            self.assertEqual(result.benchmark_price, round(bench, 6))
            self.assertEqual(result.timing, expected_timing)
            self.assertEqual(result.slippage, expected_slippage)

        self.assertEqual(len({result.timing for result in results.values()}), 3)
        self.assertEqual(len({result.slippage for result in results.values()}), 3)

    def test_sell_side_preserves_adverse_cost_sign(self):
        sell = dict(self.fill, side="sell")
        result = td.decompose_fill(
            sell, self.bars, benchmark="twap",
            commission_bps=0.0, impact_coef=0.0,
        )
        bench = result.benchmark_price
        arrival = result.arrival_price
        self.assertEqual(
            result.timing,
            round(-1 * (bench - arrival) / arrival * 10_000, 2),
        )
        self.assertEqual(
            result.slippage,
            round(-1 * (sell["price"] - bench) / bench * 10_000, 2),
        )


if __name__ == "__main__":
    unittest.main()
