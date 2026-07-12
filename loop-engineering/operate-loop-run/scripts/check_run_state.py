#!/usr/bin/env python3
import argparse, json
from pathlib import Path

ALLOWED = {"ready", "running", "verifying", "completed", "blocked", "escalated", "cancelled"}
def main():
    p = argparse.ArgumentParser(); p.add_argument("project_root"); args = p.parse_args()
    path = Path(args.project_root).resolve() / ".loop" / "state.json"
    try: state = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc: print(f"invalid state: {exc}"); raise SystemExit(1)
    errors = []
    if state.get("status") not in ALLOWED: errors.append("unknown status")
    if not isinstance(state.get("iteration"), int) or state["iteration"] < 0: errors.append("iteration must be a non-negative integer")
    if state.get("status") in {"running", "verifying"} and not state.get("next_action"): errors.append("active state requires next_action")
    print(json.dumps({"ok": not errors, "errors": errors}, ensure_ascii=False))
    raise SystemExit(1 if errors else 0)
if __name__ == "__main__": main()
