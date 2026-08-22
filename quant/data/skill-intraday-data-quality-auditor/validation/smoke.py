from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


script = Path(__file__).resolve().parents[1] / "scripts" / "audit_bars.py"
completed = subprocess.run(
    [sys.executable, "-B", str(script), "--demo"],
    check=True,
    capture_output=True,
    text=True,
    encoding="utf-8",
)
report = json.loads(completed.stdout)
assert report["status"] in {"pass", "warning", "fail", "insufficient-evidence"}
assert report["assumptions"] and report["limitations"]
assert "domain_result" in report
print("intraday-data-quality-auditor smoke: PASS")
