#!/usr/bin/env python3
"""Read-only health scan for this skills repository.

The scan writes one JSON report only when --report is supplied. It never edits skills,
the index, Git state, or external systems. A detected repository issue is data in the
report, not a scan failure; exit status is non-zero only if the scan itself cannot finish.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

SKIP_DIRS = {".git", ".loop", "node_modules", "__pycache__", ".venv", "venv"}
ALLOWED_FRONTMATTER = {"name", "description", "license", "metadata", "allowed-tools"}
LINK_RE = re.compile(r"(?<!!)\[[^\]]*\]\(([^)]+)\)")

def files(root: Path, suffix: str):
    for path in root.rglob(f"*{suffix}"):
        if not any(part in SKIP_DIRS for part in path.relative_to(root).parts):
            yield path

def add(issues, severity, rule_id, path, message, suggestion):
    issues.append({"severity": severity, "rule_id": rule_id, "path": str(path), "message": message, "suggestion": suggestion})

def check_skills(root: Path, issues: list[dict]):
    count = 0
    for path in files(root, ".md"):
        if path.name != "SKILL.md":
            continue
        count += 1
        lines = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
        if not lines or lines[0].strip() != "---":
            add(issues, "error", "skill.frontmatter.missing", path, "SKILL.md has no YAML frontmatter", "Add name and description frontmatter or classify this file as a non-Codex artifact.")
            continue
        try:
            end = lines[1:].index("---") + 1
        except ValueError:
            add(issues, "error", "skill.frontmatter.unclosed", path, "YAML frontmatter is not closed", "Close the frontmatter with --- before the Markdown body.")
            continue
        keys = []
        values = {}
        for line in lines[1:end]:
            match = re.match(r"^([A-Za-z][A-Za-z0-9_-]*):\s*(.*)$", line)
            if match:
                keys.append(match.group(1)); values[match.group(1)] = match.group(2).strip().strip('"')
        for required in ("name", "description"):
            if not values.get(required):
                add(issues, "error", f"skill.frontmatter.{required}", path, f"Missing {required}", f"Add a non-empty {required} field.")
        if values.get("name") and values["name"] != path.parent.name and not (path.parent / "SOURCE.md").is_file():
            add(issues, "warning", "skill.name-folder-mismatch", path, f"name={values['name']} differs from folder={path.parent.name}", "Rename one side or add SOURCE.md documenting the intentional imported alias.")
        extra = sorted(set(keys) - ALLOWED_FRONTMATTER)
        if extra:
            add(issues, "review", "skill.frontmatter.noncanonical", path, f"Noncanonical frontmatter keys: {', '.join(extra)}", "Confirm the target agent accepts these keys; migrate or preserve them deliberately.")
    return count

def check_index(root: Path, issues: list[dict]):
    result = subprocess.run([sys.executable, "_meta/build_index.py", "--check"], cwd=root, text=True, capture_output=True)
    if result.returncode:
        add(issues, "error", "index.stale", root / "INDEX.md", (result.stdout + result.stderr).strip()[:2000], "Review the diff, then run python _meta/build_index.py and commit the generated index.")
    return {"exit_code": result.returncode, "output": (result.stdout + result.stderr).strip()[:2000]}

def check_python(root: Path, issues: list[dict]):
    count = 0
    for path in files(root, ".py"):
        count += 1
        try:
            compile(path.read_text(encoding="utf-8-sig"), str(path), "exec")
        except (OSError, SyntaxError, UnicodeError) as exc:
            add(issues, "error", "python.syntax", path, str(exc), "Fix the syntax error and rerun this scan.")
    return count

def check_links(root: Path, issues: list[dict]):
    count = 0
    for path in files(root, ".md"):
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        for raw in LINK_RE.findall(text):
            target = raw.strip().split(maxsplit=1)[0].strip("<>")
            if not target or target.lower() == "url" or target.startswith(("#", "http://", "https://", "mailto:", "data:")):
                continue
            target = target.split("#", 1)[0]
            if not target: continue
            count += 1
            resolved = (path.parent / target).resolve()
            if not resolved.exists():
                add(issues, "warning", "markdown.local-link-missing", path, f"Missing local target: {target}", "Repair the relative link or remove it if the target was intentionally retired.")
    return count

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--report", help="Write the JSON report here; parent directories are created.")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    if not (root / "_meta" / "build_index.py").is_file():
        raise SystemExit(f"Not a supported skills repository: {root}")
    issues = []
    report = {
        "schema_version": 1,
        "scan_id": datetime.now(timezone.utc).strftime("skills-health-%Y%m%dT%H%M%SZ"),
        "root": str(root),
        "scanned_at": datetime.now(timezone.utc).isoformat(),
        "checks": {},
        "issues": issues,
    }
    report["checks"]["skills"] = {"skill_files": check_skills(root, issues)}
    report["checks"]["index"] = check_index(root, issues)
    report["checks"]["python"] = {"python_files": check_python(root, issues)}
    report["checks"]["links"] = {"local_links": check_links(root, issues)}
    report["summary"] = {key: sum(1 for issue in issues if issue["severity"] == key) for key in ("error", "warning", "review")}
    output = json.dumps(report, ensure_ascii=False, indent=2)
    if args.report:
        out = Path(args.report).resolve(); out.parent.mkdir(parents=True, exist_ok=True); out.write_text(output + "\n", encoding="utf-8")
    print(output)

if __name__ == "__main__": main()
