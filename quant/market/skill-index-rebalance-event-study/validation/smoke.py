from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


script = Path(__file__).resolve().parents[1] / "scripts" / "study_index_rebalance.py"
completed = subprocess.run(
    [sys.executable, "-B", str(script), "--demo", "--start", "0", "--end", "1"],
    check=True,
    capture_output=True,
    text=True,
    encoding="utf-8",
)
report = json.loads(completed.stdout)
assert report["status"] == "pass"
assert len(report["domain_result"]["events"]) == 2
assert any("relative_to" in item for item in report["limitations"])
print("index-rebalance-event-study smoke: PASS")
