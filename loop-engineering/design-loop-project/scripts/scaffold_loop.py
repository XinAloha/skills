#!/usr/bin/env python3
"""Create a non-destructive, platform-neutral Loop Engineering project scaffold."""
import argparse
import json
from pathlib import Path

CONTRACT = {
    "schema_version": 1,
    "id": "replace-with-stable-task-id",
    "mode": "closed",
    "architecture": "react",
    "trigger": {"kind": "manual", "dedupe_key": "TODO", "concurrency": 1},
    "goal": {"statement": "TODO", "evidence": [], "verifier": "deterministic"},
    "allowed_actions": {"read": ["TODO"], "write": [], "external": []},
    "delivery": {"mode": "draft-pr-only", "branch": "agent/<task-id>", "pr": "draft-required"},
    "review": {"implementer_identity": "implementer", "verifier_identity": "independent-reviewer", "checklist_path": ".loop/review-checklist.md", "verdict_path": ".loop/verdicts/<task-id>.json"},
    "budgets": {"max_iterations": 5, "max_minutes": 30, "max_cost": "TODO", "max_tool_retries": 2},
    "stop_rules": {"success": "all evidence passes", "no_progress": 2, "hard_stops": [], "escalate_to": "TODO"},
    "approval_gates": ["merge", "deploy", "production-write", "external-notification"],
}
STATE = {
    "schema_version": 1, "task_id": "replace-with-stable-task-id", "status": "ready",
    "iteration": 0, "strategy_generation": 0, "budget_remaining": {}, "checkpoint": None,
    "last_evidence": [], "attempt_fingerprints": [], "assumptions": [], "next_action": "Validate contract",
}
FILES = {
    "runbook.md": "# Runbook\n\n## Prepare\nVerify contract, permissions, workspace isolation, and current evidence.\n\n## Iteration\nRead state → select one action → execute → collect evidence → run checks → append journal → update state → continue, complete, or escalate.\n\n## Recovery\nTODO: owner, rollback/reconciliation command, and resume checkpoint.\n",
    "triage.md": "# Triage Queue\n\n| id | source | evidence | risk | status | owner | next action |\n|---|---|---|---|---|---|---|\n",
    "journal.md": "# Attempt Journal\n\nAppend one entry per iteration: timestamp, task id, action, evidence, result, decision, and cost/usage if available.\n",
    "evidence.md": "# Evidence Index\n\n| timestamp | claim | source or command | result | verifier |\n|---|---|---|---|---|\n",
}

def write_if_missing(path, content):
    if path.exists(): return False
    path.write_text(content, encoding="utf-8")
    return True

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("project_root")
    args = parser.parse_args()
    root = Path(args.project_root).resolve() / ".loop"
    root.mkdir(parents=True, exist_ok=True)
    created, skipped = [], []
    for name, content in FILES.items():
        (created if write_if_missing(root / name, content) else skipped).append(name)
    for name, data in (("contract.json", CONTRACT), ("state.json", STATE)):
        path = root / name
        if path.exists(): skipped.append(name)
        else:
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            created.append(name)
    print(json.dumps({"directory": str(root), "created": created, "skipped": skipped}, ensure_ascii=False))

if __name__ == "__main__": main()

