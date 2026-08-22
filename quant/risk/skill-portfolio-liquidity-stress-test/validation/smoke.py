from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


script = Path(__file__).resolve().parents[1] / "scripts" / "stress_liquidity.py"
completed = subprocess.run(
    [sys.executable, "-B", str(script), "--demo", "--redemption-value", "50000000"],
    check=True,
    capture_output=True,
    text=True,
    encoding="utf-8",
)
report = json.loads(completed.stdout)
assert report["status"] == "warning"
assert report["domain_result"]["cash_shortfall"] > 0
assert report["assumptions"]["adv_unit"]
print("portfolio-liquidity-stress-test smoke: PASS")
