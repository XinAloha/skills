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
SCRIPT = ROOT / "scripts" / "study_index_rebalance.py"
SPEC = importlib.util.spec_from_file_location("study_index_rebalance", SCRIPT)
assert SPEC and SPEC.loader
STUDY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(STUDY)


class IndexRebalanceStudyTests(unittest.TestCase):
    def setUp(self) -> None:
        STUDY._INPUT_ISSUES.clear()

    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-B", str(SCRIPT), *args], cwd=ROOT,
            text=True, capture_output=True, check=False,
        )

    def write_csv(self, directory: str, rows: list[dict[str, str]]) -> Path:
        path = Path(directory) / "events.csv"
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        return path

    def test_demo_cli_passes(self) -> None:
        result = self.run_cli("--demo")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "pass")

    def test_cli_rejects_both_or_neither_source(self) -> None:
        self.assertEqual(self.run_cli().returncode, 2)
        self.assertEqual(self.run_cli("--demo", "--input", "unused.csv").returncode, 2)

    def test_input_cli_writes_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = self.write_csv(directory, STUDY._demo_rows(STUDY.DEMO))
            output = Path(directory) / "report.json"
            result = self.run_cli("--input", str(source), "--out", str(output))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(output.read_text(encoding="utf-8"))["status"], "pass")

    def test_reversed_or_empty_window_is_insufficient(self) -> None:
        rows = STUDY._demo_rows(STUDY.DEMO)
        self.assertEqual(STUDY.build_report(STUDY.analyze(rows, 2, -1))["status"], "insufficient-evidence")
        self.assertEqual(STUDY.build_report(STUDY.analyze(rows, 5, 6))["status"], "insufficient-evidence")

    def test_car_and_volume_are_calculated(self) -> None:
        report = STUDY.build_report(STUDY.analyze(STUDY._demo_rows(STUDY.DEMO), 0, 1))
        first = next(item for item in report["domain_result"]["events"] if item["event_id"] == "A1")
        self.assertAlmostEqual(first["car"], 0.033)
        self.assertAlmostEqual(first["mean_volume_ratio"], 1.75)

    def test_anchors_are_separate_event_panels(self) -> None:
        rows = STUDY._demo_rows(STUDY.DEMO[:2])
        rows[0]["relative_to"] = "announcement"
        rows[1]["relative_to"] = "effective"
        report = STUDY.build_report(STUDY.analyze(rows, 0, 1))
        details = report["domain_result"]["events"]
        self.assertEqual({item["anchor"] for item in details}, {"announcement", "effective"})
        self.assertEqual(len(details), 2)

    def test_anchor_whitespace_is_normalized_consistently(self) -> None:
        rows = STUDY._demo_rows(STUDY.DEMO[:2])
        rows[0]["relative_to"] = " announcement "
        rows[1]["relative_to"] = "announcement"
        report = STUDY.build_report(STUDY.analyze(rows, 0, 1))
        self.assertEqual(report["status"], "pass")
        self.assertIn("announcement", report["domain_result"]["anchor_summary"])
        self.assertEqual(report["domain_result"]["events"][0]["anchor"], "announcement")

    def test_missing_anchor_is_disclosed(self) -> None:
        report = STUDY.build_report(STUDY.analyze(STUDY._demo_rows(STUDY.DEMO), 0, 1))
        self.assertTrue(any("relative_to" in item for item in report["limitations"]))

    def test_partially_missing_anchor_is_disclosed(self) -> None:
        rows = STUDY._demo_rows(STUDY.DEMO[:2])
        rows[0]["relative_to"] = "announcement"
        report = STUDY.build_report(STUDY.analyze(rows, 0, 1))
        self.assertEqual(report["status"], "pass")
        self.assertTrue(any("relative_to" in item for item in report["limitations"]))

    def test_invalid_text_and_dates_are_insufficient(self) -> None:
        rows = STUDY._demo_rows(STUDY.DEMO)
        rows[0]["event_id"] = ""
        rows[1]["symbol"] = ""
        rows[2]["action"] = "unknown"
        rows[2]["announcement_date"] = "2024-1-1"
        self.assertEqual(STUDY.build_report(STUDY.analyze(rows, 0, 1))["status"], "insufficient-evidence")

    def test_announcement_after_effective_is_insufficient(self) -> None:
        rows = STUDY._demo_rows(STUDY.DEMO)
        rows[0]["announcement_date"] = "2024-02-01"
        self.assertEqual(STUDY.build_report(STUDY.analyze(rows, 0, 1))["status"], "insufficient-evidence")

    def test_non_integer_and_duplicate_relative_days_are_insufficient(self) -> None:
        rows = STUDY._demo_rows(STUDY.DEMO)
        rows[0]["relative_day"] = "0.5"
        self.assertEqual(STUDY.build_report(STUDY.analyze(rows, 0, 1))["status"], "insufficient-evidence")
        rows = STUDY._demo_rows(STUDY.DEMO)
        rows[1]["relative_day"] = "0"
        self.assertEqual(STUDY.build_report(STUDY.analyze(rows, 0, 1))["status"], "insufficient-evidence")

    def test_invalid_numeric_values_are_insufficient(self) -> None:
        rows = STUDY._demo_rows(STUDY.DEMO)
        rows[0]["return"] = "nan"
        rows[1]["volume_ratio"] = "-1"
        rows[2]["weight_before"] = "bad"
        self.assertEqual(STUDY.build_report(STUDY.analyze(rows, 0, 1))["status"], "insufficient-evidence")

    def test_inconsistent_event_metadata_is_insufficient(self) -> None:
        rows = STUDY._demo_rows(STUDY.DEMO[:2])
        rows[1]["symbol"] = "DIFFERENT"
        self.assertEqual(STUDY.build_report(STUDY.analyze(rows, 0, 1))["status"], "insufficient-evidence")

    def test_weight_change_is_reported(self) -> None:
        rows = STUDY._demo_rows(STUDY.DEMO[:2])
        for row in rows:
            row["action"] = "weight_change"
            row["weight_before"] = "0.02"
            row["weight_after"] = "0.03"
        report = STUDY.build_report(STUDY.analyze(rows, 0, 1))
        self.assertAlmostEqual(report["domain_result"]["events"][0]["weight_change"], 0.01)

    def test_inconsistent_weight_metadata_is_insufficient(self) -> None:
        rows = STUDY._demo_rows(STUDY.DEMO[:2])
        rows[0]["weight_before"] = "0.02"
        rows[1]["weight_before"] = "0.03"
        report = STUDY.build_report(STUDY.analyze(rows, 0, 1))
        self.assertEqual(report["status"], "insufficient-evidence")

    def test_cross_anchor_event_metadata_and_weights_must_match(self) -> None:
        base = STUDY._demo_rows(STUDY.DEMO[:2])
        base[0]["relative_to"] = "announcement"
        base[1]["relative_to"] = "effective"
        for column, conflicting_value in (("symbol", "DIFFERENT"), ("weight_before", "0.30")):
            with self.subTest(column=column):
                rows = [dict(row) for row in base]
                if column == "weight_before":
                    rows[0][column] = "0.10"
                rows[1][column] = conflicting_value
                report = STUDY.build_report(STUDY.analyze(rows, 0, 1))
                self.assertEqual(report["status"], "insufficient-evidence")

    def test_action_summary_is_separated_by_anchor(self) -> None:
        rows = STUDY._demo_rows(STUDY.DEMO[:2])
        rows[0]["relative_to"] = "announcement"
        rows[1]["relative_to"] = "effective"
        report = STUDY.build_report(STUDY.analyze(rows, 0, 1))
        summary = report["domain_result"]["action_summary"]["add"]
        self.assertEqual(set(summary), {"announcement", "effective"})
        self.assertEqual(summary["announcement"]["events"], 1)
        self.assertEqual(summary["effective"]["events"], 1)
        self.assertAlmostEqual(summary["announcement"]["mean_car"], 0.025)
        self.assertAlmostEqual(summary["effective"]["mean_car"], 0.008)

    def test_missing_columns_are_insufficient(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = self.write_csv(directory, [{"event_id": "A1", "symbol": "X"}])
            rows = STUDY.load_rows(str(source), STUDY.DEMO)
            report = STUDY.build_report(STUDY.analyze(rows, 0, 1))
            self.assertEqual(report["status"], "insufficient-evidence")

    def test_cli_reports_unreadable_inputs_as_insufficient(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            invalid_utf8 = root / "invalid.csv"
            invalid_utf8.write_bytes(b"event_id,symbol\n\xff\xfe")
            cases = (root / "missing.csv", root, invalid_utf8)
            for source in cases:
                with self.subTest(source=str(source)):
                    result = self.run_cli("--input", str(source))
                    self.assertEqual(result.returncode, 0, result.stderr)
                    payload = json.loads(result.stdout)
                    self.assertEqual(payload["status"], "insufficient-evidence")
                    reasons = {
                        item["evidence"].get("reason")
                        for item in payload["findings"]
                        if isinstance(item.get("evidence"), dict)
                    }
                    self.assertIn("input_read_error", reasons)

    def test_cli_reports_output_write_errors_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cases = (root, root / "missing-parent" / "report.json")
            for output in cases:
                with self.subTest(output=str(output)):
                    result = self.run_cli("--demo", "--out", str(output))
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertNotIn("Traceback", result.stderr)
                    payload = json.loads(result.stdout)
                    self.assertEqual(payload["status"], "insufficient-evidence")
                    reasons = {
                        item["evidence"].get("reason")
                        for item in payload["findings"]
                        if isinstance(item.get("evidence"), dict)
                    }
                    self.assertIn("output_write_error", reasons)


if __name__ == "__main__":
    unittest.main()
