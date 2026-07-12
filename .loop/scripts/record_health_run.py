#!/usr/bin/env python3
"""Persist a completed skills-health scan without touching repository source files."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

def within(path: Path, root: Path) -> Path:
    resolved = path.resolve()
    if resolved != root and root not in resolved.parents:
        raise ValueError(f"path escapes .loop: {resolved}")
    return resolved

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--report", default=".loop/reports/latest.json")
    args = parser.parse_args()
    repo = Path(args.root).resolve(); loop = repo / ".loop"
    report_path = within((repo / args.report), loop)
    report = json.loads(report_path.read_text(encoding="utf-8-sig"))
    scan_id = report["scan_id"]
    now = datetime.now(timezone.utc).isoformat()
    history = loop / "reports" / f"{scan_id}.json"
    if not history.exists(): shutil.copyfile(report_path, history)

    triage = loop / "triage.md"; existing = triage.read_text(encoding="utf-8-sig")
    rows = []
    for index, issue in enumerate(report["issues"], start=1):
        item_id = f"{scan_id}-{index:03d}"
        source = issue["rule_id"].replace("|", "\\|")
        path = issue["path"].replace("\\", "/").replace("|", "\\|")
        suggestion = issue["suggestion"].replace("|", "\\|")
        fingerprint = f"| {source} | `{path}` | {issue['severity']} |"
        if item_id in existing or fingerprint in existing: continue
        rows.append(f"| {item_id} | {source} | `{path}` | {issue['severity']} | open | repository-maintainer | {suggestion} |")
    if rows: triage.write_text(existing.rstrip() + "\n" + "\n".join(rows) + "\n", encoding="utf-8")

    active = {
        (issue["rule_id"], issue["path"].replace("\\", "/"), issue["severity"])
        for issue in report["issues"]
    }
    triage_text = triage.read_text(encoding="utf-8-sig")
    reconciled, resolved = [], 0
    for line in triage_text.splitlines():
        parts = line.split("|")
        if len(parts) >= 8 and parts[1].strip().startswith("skills-health-") and parts[5].strip() == "open":
            fingerprint = (parts[2].strip().replace("\\|", "|"), parts[3].strip().strip("`").replace("\\", "/").replace("\\|", "|"), parts[4].strip())
            if fingerprint not in active:
                parts[5] = " resolved "
                line = "|".join(parts)
                resolved += 1
        reconciled.append(line)
    if resolved:
        triage.write_text("\n".join(reconciled) + "\n", encoding="utf-8")

    summary = report["summary"]
    journal = loop / "journal.md"
    journal_text = journal.read_text(encoding="utf-8-sig")
    if f"## {scan_id}" not in journal_text:
        with journal.open("a", encoding="utf-8") as fh:
            fh.write(f"\n## {scan_id}\n\n- timestamp: {now}\n- command: `python .loop/scripts/skills_health_check.py --root . --report .loop/reports/latest.json`\n- report: `.loop/reports/{scan_id}.json`\n- summary: errors={summary['error']}, warnings={summary['warning']}, reviews={summary['review']}\n- result: completed; findings were triaged without source edits.\n")
    evidence = loop / "evidence.md"
    evidence_text = evidence.read_text(encoding="utf-8-sig")
    if scan_id not in evidence_text:
        with evidence.open("a", encoding="utf-8") as fh:
            fh.write(f"| {now} | Daily scan completed and findings were recorded. | `python .loop/scripts/record_health_run.py --root .` | `.loop/reports/{scan_id}.json` | deterministic |\n")

    state_path = loop / "state.json"; state = json.loads(state_path.read_text(encoding="utf-8-sig"))
    already_recorded = state.get("checkpoint") == scan_id and state.get("status") == "completed"
    fingerprint = hashlib.sha256(json.dumps(summary, sort_keys=True).encode()).hexdigest()[:16]
    if not already_recorded:
        state.update({
            "status": "completed", "iteration": int(state.get("iteration", 0)) + 1,
            "checkpoint": scan_id, "last_evidence": [f".loop/reports/{scan_id}.json"],
            "attempt_fingerprints": [fingerprint], "next_action": "At the next UTC daily trigger, set status to running and execute the read-only scan.",
            "updated_at": now,
        })
        state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"scan_id": scan_id, "triage_rows_added": len(rows), "triage_rows_resolved": resolved, "history_report": str(history), "already_recorded": already_recorded}, ensure_ascii=False))

if __name__ == "__main__": main()
