#!/usr/bin/env python3
import argparse, json
from pathlib import Path

REQUIRED_FILES = ("contract.json", "state.json", "runbook.md", "triage.md", "journal.md", "evidence.md")
STATE_KEYS = {"schema_version", "task_id", "status", "iteration", "strategy_generation", "budget_remaining", "checkpoint", "last_evidence", "attempt_fingerprints", "assumptions", "next_action"}
def main():
    p = argparse.ArgumentParser(); p.add_argument("project_root"); args = p.parse_args()
    root = Path(args.project_root).resolve() / ".loop"; errors, warnings = [], []
    for name in REQUIRED_FILES:
        if not (root / name).is_file(): errors.append(f"missing .loop/{name}")
    for name in ("contract.json", "state.json"):
        path = root / name
        if path.is_file():
            try: json.loads(path.read_text(encoding="utf-8-sig"))
            except (OSError, json.JSONDecodeError) as exc: errors.append(f"invalid {name}: {exc}")
    state = root / "state.json"
    if state.is_file():
        data = json.loads(state.read_text(encoding="utf-8-sig"))
        for key in STATE_KEYS - data.keys(): errors.append(f"state missing key: {key}")
        if data.get("task_id") == "replace-with-stable-task-id": warnings.append("state task id is still a scaffold value")
    contract = root / "contract.json"
    if contract.is_file() and "TODO" in contract.read_text(encoding="utf-8-sig"): warnings.append("contract has unresolved scaffold values")
    print(json.dumps({"ok": not errors, "errors": errors, "warnings": warnings}, ensure_ascii=False, indent=2))
    raise SystemExit(1 if errors else 0)
if __name__ == "__main__": main()
