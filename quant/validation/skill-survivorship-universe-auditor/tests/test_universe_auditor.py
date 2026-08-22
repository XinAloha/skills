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
SCRIPT = ROOT / "scripts" / "audit_universe.py"
SPEC = importlib.util.spec_from_file_location("audit_universe", SCRIPT)
assert SPEC and SPEC.loader
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


def valid_rows() -> list[dict[str, str]]:
    return [
        {"symbol": "A", "date": "2024-01-02", "eligible": "1", "listed_at": "2020-01-01", "delisted_at": "", "return": "0.01", "delisting_return": ""},
        {"symbol": "A", "date": "2024-01-03", "eligible": "1", "listed_at": "2020-01-01", "delisted_at": "", "return": "0.02", "delisting_return": ""},
    ]


class UniverseAuditorTests(unittest.TestCase):
    def setUp(self) -> None:
        AUDIT._INPUT_ISSUES.clear()

    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run([sys.executable, "-B", str(SCRIPT), *args], cwd=ROOT, text=True, capture_output=True, check=False)

    def write_csv(self, directory: str, rows: list[dict[str, str]]) -> Path:
        path = Path(directory) / "universe.csv"
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader(); writer.writerows(rows)
        return path

    def report(self, rows: list[dict[str, str]]):
        return AUDIT.build_report(AUDIT.analyze(rows))

    def test_demo_cli_reports_findings(self) -> None:
        result = self.run_cli("--demo")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "fail")

    def test_cli_rejects_both_or_neither_source(self) -> None:
        self.assertEqual(self.run_cli().returncode, 2)
        self.assertEqual(self.run_cli("--demo", "--input", "unused.csv").returncode, 2)

    def test_input_cli_writes_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = self.write_csv(directory, valid_rows())
            output = Path(directory) / "report.json"
            result = self.run_cli("--input", str(source), "--out", str(output))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(output.read_text(encoding="utf-8"))["status"], "pass")

    def test_strict_dates_and_required_listing_are_insufficient(self) -> None:
        rows = valid_rows(); rows[0]["date"] = "2024-1-2"; rows[1]["listed_at"] = ""
        self.assertEqual(self.report(rows)["status"], "insufficient-evidence")

    def test_invalid_eligibility_and_returns_are_insufficient(self) -> None:
        rows = valid_rows(); rows[0]["eligible"] = "true"; rows[1]["return"] = "nan"
        self.assertEqual(self.report(rows)["status"], "insufficient-evidence")
        rows = valid_rows(); rows[0]["return"] = "-1.1"
        self.assertEqual(self.report(rows)["status"], "insufficient-evidence")

    def test_duplicate_identity_date_is_insufficient(self) -> None:
        rows = valid_rows(); rows[1]["date"] = rows[0]["date"]
        self.assertEqual(self.report(rows)["status"], "insufficient-evidence")

    def test_inconsistent_lifecycle_is_insufficient(self) -> None:
        rows = valid_rows(); rows[1]["listed_at"] = "2021-01-01"
        self.assertEqual(self.report(rows)["status"], "insufficient-evidence")

    def test_listing_after_delisting_is_insufficient(self) -> None:
        rows = valid_rows(); rows[0]["delisted_at"] = "2019-01-01"; rows[1]["delisted_at"] = "2019-01-01"
        self.assertEqual(self.report(rows)["status"], "insufficient-evidence")

    def test_lifecycle_membership_violations_fail(self) -> None:
        rows = valid_rows(); rows[0]["date"] = "2019-12-31"
        self.assertEqual(self.report(rows)["status"], "fail")
        rows = valid_rows()
        for row in rows: row["delisted_at"] = "2024-01-02"
        rows[1]["date"] = "2024-01-03"
        self.assertEqual(self.report(rows)["status"], "fail")

    def test_delisting_date_remains_in_universe_when_return_missing(self) -> None:
        rows = [{"symbol": "D", "date": "2024-03-29", "eligible": "1", "listed_at": "2020-01-01", "delisted_at": "2024-03-29", "return": "", "delisting_return": ""}]
        report = self.report(rows)
        self.assertEqual(report["status"], "fail")
        self.assertEqual(report["domain_result"]["point_in_time_universe"]["2024-03-29"], ["D"])

    def test_delisting_overstatement_uses_authoritative_total_return(self) -> None:
        rows = [{"symbol": "D", "date": "2024-03-29", "eligible": "1", "listed_at": "2020-01-01", "delisted_at": "2024-03-29", "return": "0.05", "delisting_return": "-0.50"}]
        domain = self.report(rows)["domain_result"]
        self.assertAlmostEqual(domain["mean_return_overstatement_without_delisting_return"], 0.55)

    def test_all_ineligible_date_is_preserved_as_empty_snapshot(self) -> None:
        rows = [{"symbol": "A", "date": "2024-01-02", "eligible": "0", "listed_at": "2020-01-01", "delisted_at": "", "return": "", "delisting_return": ""}]
        report = self.report(rows)
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["domain_result"]["point_in_time_universe"], {"2024-01-02": []})

    def test_out_of_universe_delisting_is_excluded_from_bias_and_findings(self) -> None:
        rows = [{"symbol": "OUT", "date": "2024-01-02", "eligible": "0", "listed_at": "2020-01-01", "delisted_at": "2024-01-02", "return": "0.50", "delisting_return": "-0.50"}]
        domain = self.report(rows)["domain_result"]
        self.assertTrue(domain["passed"])
        self.assertEqual(domain["delisting_bias_observations"], 0)
        self.assertIsNone(domain["mean_return_overstatement_without_delisting_return"])

    def test_bias_aggregation_uses_only_valid_universe_members(self) -> None:
        rows = [
            {"symbol": "IN", "date": "2024-01-02", "eligible": "1", "listed_at": "2020-01-01", "delisted_at": "2024-01-02", "return": "0.10", "delisting_return": "-0.20"},
            {"symbol": "OUT", "date": "2024-01-02", "eligible": "0", "listed_at": "2020-01-01", "delisted_at": "2024-01-02", "return": "0.90", "delisting_return": "-0.90"},
        ]
        domain = self.report(rows)["domain_result"]
        self.assertEqual(domain["point_in_time_universe"], {"2024-01-02": ["IN"]})
        self.assertEqual(domain["delisting_bias_observations"], 1)
        self.assertAlmostEqual(domain["mean_return_overstatement_without_delisting_return"], 0.30)

    def test_stable_id_links_ticker_changes(self) -> None:
        rows = valid_rows(); rows[0]["symbol"] = "OLD"; rows[1]["symbol"] = "NEW"
        for row in rows: row["stable_id"] = "SEC-1"
        report = self.report(rows)
        self.assertEqual(report["domain_result"]["symbols"], 1)
        self.assertFalse(any("stable_id" in item for item in report["limitations"]))

    def test_inconsistent_stable_id_mapping_is_insufficient(self) -> None:
        rows = valid_rows()
        rows[0]["stable_id"] = "SEC-1"
        rows[1]["stable_id"] = "SEC-2"
        self.assertEqual(self.report(rows)["status"], "insufficient-evidence")
        rows = valid_rows()
        rows[0]["stable_id"] = "SEC-1"
        self.assertEqual(self.report(rows)["status"], "insufficient-evidence")

    def test_missing_stable_id_is_disclosed(self) -> None:
        self.assertTrue(any("stable_id" in item for item in self.report(valid_rows())["limitations"]))

    def test_missing_columns_are_insufficient(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = self.write_csv(directory, [{"symbol": "X"}])
            rows = AUDIT.load_rows(str(source), AUDIT.DEMO)
            report = AUDIT.build_report(AUDIT.analyze(rows))
            self.assertEqual(report["status"], "insufficient-evidence")
            self.assertEqual(report["metrics"], {})

    def test_cli_handles_input_and_output_errors(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); invalid = root / "invalid.csv"; invalid.write_bytes(b"symbol,date\n\xff\xfe")
            for source in (root / "missing.csv", root, invalid):
                result = self.run_cli("--input", str(source))
                self.assertEqual(json.loads(result.stdout)["status"], "insufficient-evidence")
                self.assertNotIn("Traceback", result.stderr)
            for output in (root, root / "missing-parent" / "report.json"):
                result = self.run_cli("--demo", "--out", str(output))
                self.assertEqual(json.loads(result.stdout)["status"], "insufficient-evidence")
                self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
