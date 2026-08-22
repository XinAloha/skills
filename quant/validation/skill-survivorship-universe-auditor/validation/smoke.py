from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


script = Path(__file__).resolve().parents[1] / "scripts" / "audit_universe.py"
completed = subprocess.run(
    [sys.executable, "-B", str(script), "--demo"],
    check=True,
    capture_output=True,
    text=True,
    encoding="utf-8",
)
report = json.loads(completed.stdout)
assert report["status"] == "fail"
assert "point_in_time_universe" in report["domain_result"]
assert report["assumptions"]["eligible_encoding"] == "0 or 1"
print("survivorship-universe-auditor smoke: PASS")
