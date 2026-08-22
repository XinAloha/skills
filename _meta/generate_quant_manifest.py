#!/usr/bin/env python3
"""Generate import-manifest rows for quantskills catalog skills.

Reads _quant_skill_list.txt (name \t category \t subcategory \t url \t summary_zh),
maps category -> quant/<subdir>, infers kind from the cloned repo layout, and
appends rows to import-manifest.tsv (or prints them).
"""
from __future__ import annotations
import csv
import sys
from pathlib import Path

SKILLS = Path(__file__).resolve().parent.parent
EXTERNAL = SKILLS / "_external_skills"
MANIFEST = SKILLS / "_meta" / "import-manifest.tsv"
LIST = EXTERNAL / "_quant_skill_list.txt"
SKILLS_DIR = EXTERNAL / "quantskills-skills"

# catalog category -> quant/<subdir>
CATEGORY_MAP = {
    "01": "data",
    "02": "factors",
    "03": "market",
    "04": "risk",
    "05": "backtest",
    "06": "models",
    "07": "validation",
    "08": "news",
    "09": "agents",
    "10": "infra",
}

COMPOSITE_MARKERS = ["references", "scripts", "templates", "assets", "evals"]


def infer_kind(name: str) -> str:
    d = SKILLS_DIR / name
    if not d.exists():
        return "atomic"  # not cloned yet; default
    has = [m for m in COMPOSITE_MARKERS if (d / m).is_dir()]
    return "composite" if has else "atomic"


def main() -> None:
    rows = []
    with LIST.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.rstrip("\n")
            if not line.strip():
                continue
            parts = line.split("\t")
            if len(parts) < 5:
                continue
            name, category, subcategory, url, summary = parts[0], parts[1], parts[2], parts[3], parts[4]
            subdir = CATEGORY_MAP.get(category, "misc")
            source = f"quantskills-skills/{name}"
            target = f"quant/{subdir}/{name}"
            kind = infer_kind(name)
            rows.append({
                "source_subpath": source,
                "target_subpath": target,
                "kind": kind,
                "repo": f"quantskills/{name}",
                "repo_path": "/",
                "cluster": "-",
                "notes": summary.strip(),
            })

    if "--print" in sys.argv:
        w = csv.DictWriter(sys.stdout, fieldnames=list(rows[0].keys()), delimiter="\t", lineterminator="\n")
        for r in rows:
            w.writerow(r)
        return

    # Append to manifest (skip rows whose target already exists)
    existing = set()
    if MANIFEST.exists():
        with MANIFEST.open(encoding="utf-8") as fh:
            for r in csv.DictReader(fh, delimiter="\t"):
                if r.get("target_subpath"):
                    existing.add(r["target_subpath"])
    added = 0
    with MANIFEST.open("a", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()), delimiter="\t", lineterminator="\r\n")
        for r in rows:
            if r["target_subpath"] in existing:
                continue
            w.writerow(r)
            added += 1
    print(f"Appended {added} new rows to import-manifest.tsv (total listed {len(rows)})")


if __name__ == "__main__":
    main()
