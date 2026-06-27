#!/usr/bin/env python3
"""Import external skills per _meta/import-manifest.tsv.

For each row: copy <_external_skills>/<source_subpath> tree into <skills>/<target_subpath>,
then write a SOURCE.md sidecar with upstream URL, kind, symlink-mount snippet, and related skills.
"""
from __future__ import annotations
import csv
import shutil
from pathlib import Path
from collections import defaultdict

SKILLS = Path(__file__).resolve().parent.parent
EXTERNAL = SKILLS / "_external_skills"
MANIFEST = SKILLS / "_meta" / "import-manifest.tsv"
IMPORT_DATE = "2026-06-27"


def load_manifest() -> list[dict]:
    with MANIFEST.open(encoding="utf-8") as fh:
        rdr = csv.DictReader(fh, delimiter="\t")
        rows = [r for r in rdr if r.get("source_subpath")]
    return rows


def build_cluster_index(rows: list[dict]) -> dict[str, list[dict]]:
    idx: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        cluster = r["cluster"].strip()
        if cluster and cluster != "-":
            idx[cluster].append(r)
    return idx


def render_source_md(row: dict, cluster_idx: dict[str, list[dict]]) -> str:
    target = row["target_subpath"]
    slug = Path(target).name
    repo = row["repo"]
    repo_url = f"https://github.com/{repo}"
    repo_path = row["repo_path"] if row["repo_path"] != "/" else ""
    # canonical upstream URL for this skill
    if repo_path:
        clean_path = repo_path.lstrip("/")
        upstream_skill = f"{repo_url}/tree/main/{clean_path}"
    else:
        upstream_skill = repo_url
    kind = row["kind"]
    notes = row["notes"]
    cluster = row["cluster"].strip()

    related_lines = []
    if cluster and cluster != "-":
        siblings = [r for r in cluster_idx.get(cluster, []) if r["target_subpath"] != target]
        for s in siblings:
            sib_target = s["target_subpath"]
            sib_slug = Path(sib_target).name
            related_lines.append(f"- [{sib_slug}](../../{sib_target}/) — {s['notes'].split('.')[0].strip()}.")

    related_block = "\n".join(related_lines) if related_lines else "_(none in cluster)_"

    danger_warning = ""
    if "danger" in kind:
        danger_warning = (
            "\n> ⚠️ **DANGER**: This skill depends on reverse-engineered / unofficial APIs. "
            "Authentication via browser session, cookies, or fragile endpoints. "
            "Upstream may break without notice. Use at your own risk.\n"
        )

    return f"""# Source — `{slug}`

> Upstream tracking file. Do **not** edit `SKILL.md` here without recording the divergence in **Local modifications** below.
{danger_warning}
## Upstream

| Field | Value |
|---|---|
| Repository | [{repo}]({repo_url}) |
| Skill path in repo | `{row['repo_path']}` |
| Canonical URL | [{upstream_skill}]({upstream_skill}) |
| Kind | `{kind}` |
| Cluster | `{cluster}` |
| Imported on | {IMPORT_DATE} |
| License | see upstream `LICENSE` |

**Summary.** {notes}

## Related skills (same cluster)

{related_block}

## Mounting into another project

This skill folder is self-contained. To use it elsewhere without copying:

```bash
# from the target project root
ln -s /absolute/path/to/skills/{target}/ ./.claude/skills/{slug}
# or, on Windows (PowerShell, admin):
# New-Item -ItemType Junction -Path .\\.claude\\skills\\{slug} -Target E:\\Project\\Quantitative_Trading\\skills\\{target}
```

If your agent reads from `skill/<name>/SKILL.md`, only the `SKILL.md` is strictly required; `scripts/`, `references/`, and `assets/` are referenced by relative paths inside `SKILL.md`.

## Updating from upstream

1. Pull the latest from `{repo_url}`.
2. Copy `{row['repo_path']}` over `skills/{target}/`, **preserving this `SOURCE.md`**.
3. Reconcile any entries listed under **Local modifications** below.
4. Update the `Imported on` date above and add a short note describing what changed.

## Local modifications

_(None at import time. Record edits here when they are made: date, reason, files touched.)_
"""


def copy_skill(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns(".git", ".github", "__pycache__", "node_modules"))


def main() -> None:
    rows = load_manifest()
    cluster_idx = build_cluster_index(rows)

    copied = []
    missing = []
    for row in rows:
        src = EXTERNAL / row["source_subpath"]
        dst = SKILLS / row["target_subpath"]
        if not src.exists():
            missing.append((row["source_subpath"], row["target_subpath"]))
            continue
        copy_skill(src, dst)
        (dst / "SOURCE.md").write_text(render_source_md(row, cluster_idx), encoding="utf-8")
        copied.append(row["target_subpath"])

    print(f"Copied: {len(copied)} skills")
    for t in copied:
        print(f"  + {t}")
    if missing:
        print(f"\nMissing sources: {len(missing)}")
        for s, t in missing:
            print(f"  ! {s} -> {t}")


if __name__ == "__main__":
    main()
