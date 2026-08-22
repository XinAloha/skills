from __future__ import annotations

import csv
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "audit_adjustments.py"
SPEC = importlib.util.spec_from_file_location("audit_adjustments", SCRIPT)
assert SPEC and SPEC.loader
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


def clean_split_rows() -> list[dict[str, str]]:
    return [
        {"symbol": "X", "date": "2025-01-01", "close": "100", "adj_close": "50", "split_factor": "1", "cash_dividend": "0"},
        {"symbol": "X", "date": "2025-01-02", "close": "50", "adj_close": "50", "split_factor": "2", "cash_dividend": "0"},
    ]


class CorporateActionAuditorTests(unittest.TestCase):
    def setUp(self) -> None:
        AUDIT._INPUT_ISSUES.clear()

    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-B", str(SCRIPT), *args],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def write_csv(self, directory: str, rows: list[dict[str, str]]) -> Path:
        path = Path(directory) / "actions.csv"
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        return path

    def test_demo_cli_emits_valid_json(self) -> None:
        result = self.run_cli("--demo")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "fail")
        self.assertEqual(payload["input_summary"]["rows"], 3)

    def test_input_cli_writes_output_and_thresholds(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = self.write_csv(directory, clean_split_rows())
            output = Path(directory) / "report.json"
            result = self.run_cli(
                "--input", str(source), "--return-tolerance", "0.01",
                "--jump-threshold", "0.25", "--out", str(output),
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(payload["status"], "pass")
            self.assertEqual(payload["assumptions"]["return_tolerance"], 0.01)
            self.assertEqual(payload["assumptions"]["jump_threshold"], 0.25)

    def test_cli_rejects_both_sources(self) -> None:
        self.assertEqual(self.run_cli("--demo", "--input", "unused.csv").returncode, 2)

    def test_cli_rejects_missing_source(self) -> None:
        self.assertEqual(self.run_cli().returncode, 2)

    def test_clean_split_passes(self) -> None:
        report = AUDIT.build_report(AUDIT.analyze(clean_split_rows()))
        self.assertEqual(report["status"], "pass")

    def test_clean_cash_dividend_passes(self) -> None:
        rows = [
            {"symbol": "X", "date": "2025-01-01", "close": "100", "adj_close": "100", "split_factor": "1", "cash_dividend": "0"},
            {"symbol": "X", "date": "2025-01-02", "close": "99", "adj_close": "100", "split_factor": "1", "cash_dividend": "1"},
        ]
        self.assertEqual(AUDIT.build_report(AUDIT.analyze(rows))["status"], "pass")

    def test_adjusted_return_mismatch_fails(self) -> None:
        rows = clean_split_rows()
        rows[1]["adj_close"] = "55"
        report = AUDIT.build_report(AUDIT.analyze(rows))
        self.assertEqual(report["status"], "fail")
        self.assertIn("adjusted_return_mismatch", report["domain_result"]["findings"][0]["reasons"])

    def test_unexplained_jump_fails(self) -> None:
        report = AUDIT.build_report(AUDIT.analyze(AUDIT._demo_rows(AUDIT.DEMO)))
        reasons = [reason for finding in report["domain_result"]["findings"] for reason in finding["reasons"]]
        self.assertIn("large_unexplained_raw_price_jump", reasons)

    def test_invalid_parameters_are_insufficient_evidence(self) -> None:
        report = AUDIT.build_report(AUDIT.analyze(clean_split_rows(), -0.01, 0))
        self.assertEqual(report["status"], "insufficient-evidence")
        self.assertTrue(report["domain_result"]["analysis_skipped"])

    def test_non_finite_thresholds_are_insufficient_evidence(self) -> None:
        for return_tolerance, jump_threshold in (
            (float("nan"), 0.40),
            (float("inf"), 0.40),
            (0.02, float("nan")),
            (0.02, float("inf")),
        ):
            with self.subTest(return_tolerance=return_tolerance, jump_threshold=jump_threshold):
                report = AUDIT.build_report(
                    AUDIT.analyze(clean_split_rows(), return_tolerance, jump_threshold)
                )
                self.assertEqual(report["status"], "insufficient-evidence")

    def test_cli_reports_non_finite_thresholds_as_insufficient_evidence(self) -> None:
        result = self.run_cli("--demo", "--return-tolerance", "inf", "--jump-threshold", "nan")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "insufficient-evidence")

    def test_invalid_event_inputs_are_insufficient_evidence(self) -> None:
        rows = clean_split_rows()
        rows[0]["split_factor"] = "0"
        rows[1]["cash_dividend"] = "-1"
        report = AUDIT.build_report(AUDIT.analyze(rows))
        self.assertEqual(report["status"], "insufficient-evidence")

    def test_strict_date_duplicate_and_empty_symbol_are_rejected(self) -> None:
        rows = clean_split_rows()
        rows[0]["symbol"] = ""
        rows[1]["date"] = "2025-1-2"
        rows.append(dict(rows[1]))
        report = AUDIT.build_report(AUDIT.analyze(rows))
        self.assertEqual(report["status"], "insufficient-evidence")
        evidence = [finding["evidence"] for finding in report["findings"]]
        reasons = {item.get("reason") for item in evidence if isinstance(item, dict)}
        self.assertTrue({"empty_symbol", "invalid_date", "duplicate_symbol_date"} <= reasons)

    def test_missing_columns_are_insufficient_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = self.write_csv(directory, [{"symbol": "X", "date": "2025-01-01"}])
            rows = AUDIT.load_rows(str(source), AUDIT.DEMO)
            report = AUDIT.build_report(AUDIT.analyze(rows))
            self.assertEqual(report["status"], "insufficient-evidence")
            self.assertTrue(report["domain_result"]["analysis_skipped"])

    def test_cli_handles_missing_terminal_text_values(self) -> None:
        cases = (
            (
                "date,close,adj_close,split_factor,cash_dividend,symbol\n"
                "2025-01-01,100,100,1,0\n",
                "empty_symbol",
            ),
            (
                "symbol,close,adj_close,split_factor,cash_dividend,date\n"
                "X,100,100,1,0\n",
                "invalid_date",
            ),
        )
        for content, reason in cases:
            with self.subTest(reason=reason), tempfile.TemporaryDirectory() as directory:
                source = Path(directory) / "missing-terminal-value.csv"
                source.write_text(content, encoding="utf-8")
                result = self.run_cli("--input", str(source))
                self.assertEqual(result.returncode, 0, result.stderr)
                payload = json.loads(result.stdout)
                self.assertEqual(payload["status"], "insufficient-evidence")
                evidence = [finding["evidence"] for finding in payload["findings"]]
                self.assertTrue(any(isinstance(item, dict) and item.get("reason") == reason for item in evidence))

    def test_non_positive_price_is_insufficient_evidence(self) -> None:
        rows = clean_split_rows()
        rows[0]["close"] = "0"
        report = AUDIT.build_report(AUDIT.analyze(rows))
        self.assertEqual(report["status"], "insufficient-evidence")
        reasons = {finding["evidence"].get("reason") for finding in report["findings"]}
        self.assertIn("non_positive_price", reasons)

    def test_single_row_is_insufficient_evidence(self) -> None:
        report = AUDIT.build_report(AUDIT.analyze(clean_split_rows()[:1]))
        self.assertEqual(report["status"], "insufficient-evidence")
        reasons = {finding["evidence"].get("reason") for finding in report["findings"]}
        self.assertIn("insufficient_symbol_history", reasons)

    def test_surrounding_symbol_whitespace_is_rejected(self) -> None:
        rows = clean_split_rows()
        rows[1]["symbol"] = " X"
        report = AUDIT.build_report(AUDIT.analyze(rows))
        self.assertEqual(report["status"], "insufficient-evidence")
        reasons = {finding["evidence"].get("reason") for finding in report["findings"]}
        self.assertIn("symbol_surrounding_whitespace", reasons)


if __name__ == "__main__":
    unittest.main()
