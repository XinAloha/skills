from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "audit_bars", ROOT / "scripts" / "audit_bars.py"
)
assert SPEC and SPEC.loader
AUDIT_BARS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT_BARS)


def row(timestamp: str, session: str = "morning") -> dict[str, str]:
    return {
        "symbol": "X",
        "trading_date": "2025-01-02",
        "session": session,
        "timestamp": timestamp,
        "open": "10",
        "high": "10.1",
        "low": "9.9",
        "close": "10",
        "volume": "100",
    }


class AuditBarsTests(unittest.TestCase):
    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-B", str(ROOT / "scripts" / "audit_bars.py"), *args],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )

    def test_cli_demo_only_succeeds(self) -> None:
        completed = self.run_cli("--demo")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn(json.loads(completed.stdout)["status"], {"warning", "fail"})

    def test_cli_input_only_succeeds(self) -> None:
        csv_text = (
            "symbol,trading_date,session,timestamp,open,high,low,close,volume\n"
            "X,2025-01-02,morning,2025-01-02T09:30:00,10,10.1,9.9,10,100\n"
        )
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", encoding="utf-8", newline="", delete=False
        ) as handle:
            handle.write(csv_text)
            input_path = handle.name
        try:
            completed = self.run_cli("--input", input_path)
        finally:
            Path(input_path).unlink(missing_ok=True)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(completed.stdout)["status"], "pass")

    def test_cli_rejects_demo_and_input_together(self) -> None:
        completed = self.run_cli("--demo", "--input", "unused.csv")
        self.assertEqual(completed.returncode, 2)
        self.assertIn("not allowed with argument", completed.stderr)

    def test_cli_rejects_missing_source_mode(self) -> None:
        completed = self.run_cli()
        self.assertEqual(completed.returncode, 2)
        self.assertIn("one of the arguments", completed.stderr)

    def test_cli_non_positive_interval_returns_json_evidence_status(self) -> None:
        completed = self.run_cli("--demo", "--expected-seconds", "0")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout)["status"], "insufficient-evidence"
        )

    def test_clean_minute_bars_pass(self) -> None:
        rows = [row(f"2025-01-02T09:{minute:02d}:00") for minute in (30, 31, 32)]
        report = AUDIT_BARS.build_report(AUDIT_BARS.analyze(rows, 60))
        self.assertEqual(report["status"], "pass")

    def test_original_input_order_inversion_is_detected(self) -> None:
        result = AUDIT_BARS.analyze(
            [row("2025-01-02T09:31:00"), row("2025-01-02T09:30:00")], 60
        )
        reasons = {
            reason
            for finding in result["findings"]
            for reason in finding.get("reasons", [])
        }
        self.assertIn("non_increasing_timestamp", reasons)

    def test_explicit_night_session_allows_prior_calendar_date(self) -> None:
        rows = [
            row(f"2025-01-01T21:{minute:02d}:00", session="night")
            for minute in (0, 1)
        ]
        report = AUDIT_BARS.build_report(AUDIT_BARS.analyze(rows, 60))
        self.assertEqual(report["status"], "pass")

    def test_mixed_timezone_awareness_is_insufficient_evidence(self) -> None:
        rows = [
            row("2025-01-02T09:30:00"),
            row("2025-01-02T09:31:00+08:00"),
        ]
        report = AUDIT_BARS.build_report(AUDIT_BARS.analyze(rows, 60))
        self.assertEqual(report["status"], "insufficient-evidence")
        self.assertTrue(report["domain_result"]["analysis_skipped"])
        self.assertEqual(
            report["findings"][0]["evidence"]["reason"],
            "mixed_timezone_awareness",
        )

    def test_non_positive_expected_seconds_is_insufficient_evidence(self) -> None:
        report = AUDIT_BARS.build_report(
            AUDIT_BARS.analyze([row("2025-01-02T09:30:00")], 0)
        )
        self.assertEqual(report["status"], "insufficient-evidence")


if __name__ == "__main__":
    unittest.main()
