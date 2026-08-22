from __future__ import annotations

import csv
import importlib.util
import json
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "stress_liquidity.py"
SPEC = importlib.util.spec_from_file_location("stress_liquidity", SCRIPT)
assert SPEC and SPEC.loader
STRESS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(STRESS)


class LiquidityStressTests(unittest.TestCase):
    def setUp(self) -> None:
        STRESS._INPUT_ISSUES.clear()

    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run([sys.executable, "-B", str(SCRIPT), *args], cwd=ROOT, text=True, capture_output=True, check=False)

    def write_csv(self, directory: str, rows: list[dict[str, str]]) -> Path:
        path = Path(directory) / "holdings.csv"
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader(); writer.writerows(rows)
        return path

    def analyze(self, rows: list[dict[str, str]] | None = None, redemption: float | None = None):
        return STRESS.build_report(STRESS.analyze(rows or STRESS._demo_rows(STRESS.DEMO), 0.1, 0.5, 5, 0.5, redemption))

    def test_demo_cli_is_valid_json(self) -> None:
        result = self.run_cli("--demo")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(json.loads(result.stdout)["status"], {"pass", "warning"})

    def test_cli_rejects_both_or_neither_source(self) -> None:
        self.assertEqual(self.run_cli().returncode, 2)
        self.assertEqual(self.run_cli("--demo", "--input", "unused.csv").returncode, 2)

    def test_input_cli_writes_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = self.write_csv(directory, STRESS._demo_rows(STRESS.DEMO))
            output = Path(directory) / "report.json"
            result = self.run_cli("--input", str(source), "--out", str(output))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(json.loads(output.read_text(encoding="utf-8"))["status"], {"pass", "warning"})

    def test_non_finite_or_invalid_parameters_are_insufficient(self) -> None:
        rows = STRESS._demo_rows(STRESS.DEMO)
        cases = ((float("nan"), 0.5, 5, 0.5, None), (0.1, float("inf"), 5, 0.5, None), (0.1, 0.5, 0, 0.5, None), (0.1, 0.5, 5, -1, None), (0.1, 0.5, 5, 0.5, float("inf")))
        for args in cases:
            with self.subTest(args=args):
                self.assertEqual(STRESS.build_report(STRESS.analyze(rows, *args))["status"], "insufficient-evidence")

    def test_cli_rejects_horizon_beyond_float_range_without_traceback(self) -> None:
        huge_horizon = "1" + "0" * 400
        result = self.run_cli("--demo", "--horizon-days", huge_horizon)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "insufficient-evidence")

    def test_invalid_rows_and_duplicate_symbols_are_insufficient(self) -> None:
        rows = STRESS._demo_rows(STRESS.DEMO)
        rows[0]["symbol"] = ""
        rows[1]["adv"] = "0"
        self.assertEqual(self.analyze(rows)["status"], "insufficient-evidence")
        rows = STRESS._demo_rows(STRESS.DEMO)
        rows[1]["symbol"] = rows[0]["symbol"]
        self.assertEqual(self.analyze(rows)["status"], "insufficient-evidence")

    def test_small_redemption_cost_uses_only_planned_sales(self) -> None:
        report = self.analyze(redemption=600_000)
        domain = report["domain_result"]
        self.assertAlmostEqual(domain["redemption_cash_raised"], 600_000)
        self.assertLess(domain["redemption_cash_raised"], domain["horizon_cash_raised"])
        self.assertAlmostEqual(sum(item["redemption_cash_raised"] for item in domain["details"]), 600_000)

    def test_redemption_is_allocated_pro_rata(self) -> None:
        report = self.analyze(redemption=600_000)
        allocations = {item["symbol"]: item["redemption_allocation"] for item in report["domain_result"]["details"]}
        self.assertAlmostEqual(allocations["AAA"], 400_000)
        self.assertAlmostEqual(allocations["BBB"], 200_000)

    def test_shortfall_is_reported(self) -> None:
        report = self.analyze(redemption=50_000_000)
        self.assertEqual(report["status"], "warning")
        self.assertGreater(report["domain_result"]["cash_shortfall"], 0)

    def test_capacity_and_cost_are_finite(self) -> None:
        domain = self.analyze()["domain_result"]
        self.assertGreaterEqual(domain["portfolio_liquidated_ratio"], 0)
        self.assertLessEqual(domain["portfolio_liquidated_ratio"], 1)
        self.assertTrue(all(math.isfinite(item["estimated_cost"]) for item in domain["details"]))

    def test_longer_horizon_reduces_non_binding_impact_cost(self) -> None:
        rows = STRESS._demo_rows(STRESS.DEMO)
        one_day = STRESS.build_report(STRESS.analyze(rows, 0.1, 0.5, 1, 0.5, 60_000))["domain_result"]
        five_days = STRESS.build_report(STRESS.analyze(rows, 0.1, 0.5, 5, 0.5, 60_000))["domain_result"]
        self.assertEqual(one_day["cash_shortfall"], 0)
        self.assertEqual(five_days["cash_shortfall"], 0)
        self.assertLess(five_days["estimated_cost"], one_day["estimated_cost"])

    def test_zero_redemption_has_zero_cost(self) -> None:
        domain = self.analyze(redemption=0)["domain_result"]
        self.assertEqual(domain["redemption_cash_raised"], 0)
        self.assertEqual(domain["estimated_cost"], 0)

    def test_extreme_finite_values_do_not_overflow_or_oversell(self) -> None:
        stable = [{"symbol": "X", "position_value": "1e250", "adv": "1e250", "spread_bps": "1", "volatility": "0.01"}]
        report = STRESS.build_report(STRESS.analyze(stable, 0.1, 1.0, 5, 0.5, 1e100))
        self.assertEqual(report["status"], "pass")
        self.assertAlmostEqual(report["domain_result"]["redemption_cash_raised"], 1e100)

        overflowing_total = [
            {"symbol": "X", "position_value": "1e308", "adv": "1e308", "spread_bps": "1", "volatility": "0.01"},
            {"symbol": "Y", "position_value": "1e308", "adv": "1e308", "spread_bps": "1", "volatility": "0.01"},
        ]
        self.assertEqual(STRESS.build_report(STRESS.analyze(overflowing_total, 0.1, 1.0, 5, 0.5))["status"], "insufficient-evidence")

    def test_underflow_and_cost_overflow_are_insufficient(self) -> None:
        underflow = [{"symbol": "X", "position_value": "1", "adv": "5e-324", "spread_bps": "1", "volatility": "0.01"}]
        self.assertEqual(STRESS.build_report(STRESS.analyze(underflow, 0.1, 0.5, 5, 0.5))["status"], "insufficient-evidence")
        cost_overflow = [{"symbol": "X", "position_value": "1e308", "adv": "1e308", "spread_bps": "1e308", "volatility": "0.01"}]
        self.assertEqual(STRESS.build_report(STRESS.analyze(cost_overflow, 0.1, 1.0, 5, 0.5))["status"], "insufficient-evidence")

    def test_missing_columns_are_insufficient(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = self.write_csv(directory, [{"symbol": "X"}])
            rows = STRESS.load_rows(str(source), STRESS.DEMO)
            self.assertEqual(STRESS.build_report(STRESS.analyze(rows, 0.1, 0.5, 5, 0.5))["status"], "insufficient-evidence")

    def test_cli_handles_input_and_output_path_errors(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            invalid_utf8 = root / "invalid.csv"
            invalid_utf8.write_bytes(b"symbol,position_value\n\xff\xfe")
            for source in (root / "missing.csv", root, invalid_utf8):
                with self.subTest(input=str(source)):
                    result = self.run_cli("--input", str(source))
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(json.loads(result.stdout)["status"], "insufficient-evidence")
                    self.assertNotIn("Traceback", result.stderr)
            for output in (root, root / "missing-parent" / "report.json"):
                with self.subTest(output=str(output)):
                    result = self.run_cli("--demo", "--out", str(output))
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(json.loads(result.stdout)["status"], "insufficient-evidence")
                    self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
