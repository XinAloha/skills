from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


script = Path(__file__).resolve().parents[1] / "scripts" / "audit_adjustments.py"
completed = subprocess.run(
    [sys.executable, "-B", str(script), "--demo"],
    check=True,
    capture_output=True,
    text=True,
    encoding="utf-8",
)
report = json.loads(completed.stdout)
assert report["assumptions"]["return_tolerance"] == 0.02
assert report["domain_result"]["findings"]
assert report["status"] == "fail"
print("corporate-action-adjustment-auditor smoke: PASS")
