#!/usr/bin/env python3
import argparse, json
from pathlib import Path

REQUIRED = {"schema_version", "id", "mode", "architecture", "trigger", "goal", "allowed_actions", "budgets", "stop_rules", "approval_gates"}
NESTED = {"trigger": {"kind", "dedupe_key", "concurrency"}, "goal": {"statement", "evidence", "verifier"}, "budgets": {"max_iterations", "max_minutes", "max_cost", "max_tool_retries"}, "stop_rules": {"success", "no_progress", "hard_stops", "escalate_to"}}

def main():
    p = argparse.ArgumentParser(); p.add_argument("project_root"); args = p.parse_args()
    path = Path(args.project_root).resolve() / ".loop" / "contract.json"
    errors, warnings = [], []
    try: data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc: errors.append(f"invalid contract.json: {exc}"); data = {}
    for key in REQUIRED - data.keys(): errors.append(f"missing top-level key: {key}")
    for parent, keys in NESTED.items():
        value = data.get(parent, {})
        if not isinstance(value, dict): errors.append(f"{parent} must be an object"); continue
        for key in keys - value.keys(): errors.append(f"missing {parent}.{key}")
    if data.get("goal", {}).get("statement") in ("", "TODO"): warnings.append("goal is not yet concrete")
    if not data.get("goal", {}).get("evidence"): warnings.append("goal has no automatic evidence; require an approval gate")
    if data.get("trigger", {}).get("dedupe_key") == "TODO": warnings.append("dedupe key is not configured")
    print(json.dumps({"ok": not errors, "errors": errors, "warnings": warnings}, ensure_ascii=False, indent=2))
    raise SystemExit(1 if errors else 0)
if __name__ == "__main__": main()
