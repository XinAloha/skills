#!/usr/bin/env python3
"""Generate skills/INDEX.md from _meta/import-manifest.tsv plus pre-existing native skills.

The INDEX is the machine/human readable registry. Imports are auto-listed from the manifest;
native skills (those already in the repo before this import) are listed by walking the existing
top-level category dirs but skipping any path that matches an imported target.
"""
from __future__ import annotations
import csv
from pathlib import Path
from collections import defaultdict

SKILLS = Path(__file__).resolve().parent.parent
MANIFEST = SKILLS / "_meta" / "import-manifest.tsv"
OUT = SKILLS / "INDEX.md"

# Categories presented in this order
CATEGORY_ORDER = [
    "engineering", "testing", "git", "governance", "methodology", "workmode",
    "meta", "misc", "domain", "agent-adapters",
    "content", "productivity", "business", "ai-backends",
]

CATEGORY_BLURB = {
    "engineering": "Code/infra: style, interfaces, docs, integration, security, diagrams, app extraction.",
    "testing": "Tests & quality: collectors, DB, data quality, recovery, pipeline tests.",
    "git": "Git workflow + release engineering.",
    "governance": "Project governance: cleanup, anti-patterns, requirement abstraction, refactor checks.",
    "methodology": "Method-style skills: diagnose, decision systems, learning, deconstruction, research frameworks.",
    "workmode": "Work modes: caveman, ponytail (lazy minimal coding), grill-me, handoff, slow-is-fast, goal clarification.",
    "meta": "Meta capabilities: skill authoring, knowledge-base hygiene.",
    "misc": "Low-frequency helpers and tool references.",
    "domain": "Domain skills (e.g. A-share data tools).",
    "agent-adapters": "Platform adapter layer: same responsibility across Codex / Claude Code / etc.",
    "content": "Writing, formatting, translation, illustration, slides, social cards, publishing.",
    "productivity": "URL/video extraction, storage hygiene, notebook querying, news, summarization.",
    "business": "Business / product / personal diagnostic frameworks (dontbesilent toolkit).",
    "ai-backends": "AI provider adapters (image gen, gemini-web, etc.).",
}


def load_imports() -> tuple[list[dict], set[str]]:
    with MANIFEST.open(encoding="utf-8") as fh:
        rows = [r for r in csv.DictReader(fh, delimiter="\t") if r.get("source_subpath")]
    targets = {r["target_subpath"] for r in rows}
    return rows, targets


def list_native_skills(imported_targets: set[str]) -> list[tuple[str, str]]:
    """Walk top-level category dirs; return (category, slug) for entries not in imported_targets."""
    found = []
    for cat in CATEGORY_ORDER:
        cat_dir = SKILLS / cat
        if not cat_dir.exists():
            continue
        for entry in sorted(cat_dir.iterdir()):
            rel = f"{cat}/{entry.name}"
            if rel in imported_targets:
                continue
            # Category README.md is documentation, not a skill — skip it
            if entry.name == "README.md":
                continue
            # Skip auxiliary files; both dirs and standalone .md files count
            if entry.is_dir():
                found.append((cat, entry.name + "/"))
            elif entry.suffix == ".md":
                found.append((cat, entry.name))
    return found


def build_md(imports: list[dict], native: list[tuple[str, str]]) -> str:
    by_cat: dict[str, list[dict]] = defaultdict(list)
    for r in imports:
        cat = r["target_subpath"].split("/", 1)[0]
        by_cat[cat].append(r)

    native_by_cat: dict[str, list[str]] = defaultdict(list)
    for cat, name in native:
        native_by_cat[cat].append(name)

    out = []
    out.append("# INDEX — All skills registry")
    out.append("")
    out.append("Auto-generated companion to `README.md`. One row per skill. Re-run `_meta/build_index.py` after adding or moving skills.")
    out.append("")
    out.append("Legend for **Kind**:")
    out.append("")
    out.append("- `atomic` — single `SKILL.md`; no internal tooling. Acts as one prompt-level capability.")
    out.append("- `composite` — `SKILL.md` + bundled `scripts/` / `references/` / `assets/`. Internal multi-step logic; one self-contained pipeline.")
    out.append("- `composite-danger` — composite skill that depends on reverse-engineered or unofficial APIs; may break upstream without notice.")
    out.append("- `cluster: <name>` (in Cluster column) — multiple skills designed to be chained. See `_meta/clusters.md`.")
    out.append("- `native` — authored in this repo, not imported.")
    out.append("")

    total_imports = len(imports)
    total_native = sum(len(v) for v in native_by_cat.values())
    out.append(f"**Totals:** {total_imports} imported · {total_native} native · {total_imports + total_native} skills across {len(CATEGORY_ORDER)} categories.")
    out.append("")

    for cat in CATEGORY_ORDER:
        rows = by_cat.get(cat, [])
        nat = native_by_cat.get(cat, [])
        if not rows and not nat:
            continue
        out.append(f"## `{cat}/`")
        out.append("")
        out.append(CATEGORY_BLURB.get(cat, ""))
        out.append("")
        out.append("| Slug | Kind | Cluster | Source | Summary |")
        out.append("|---|---|---|---|---|")
        # Native first
        for name in sorted(nat):
            slug = name.rstrip("/")
            out.append(f"| [`{slug}`]({cat}/{name}) | native | — | this repo | — |")
        # Then imports
        for r in sorted(rows, key=lambda x: x["target_subpath"]):
            slug = Path(r["target_subpath"]).name
            kind = r["kind"]
            cluster = r["cluster"].strip()
            cluster_cell = cluster if cluster and cluster != "-" else "—"
            repo = r["repo"]
            repo_url = f"https://github.com/{repo}"
            repo_path = r["repo_path"].lstrip("/")
            src_url = f"{repo_url}/tree/main/{repo_path}" if repo_path else repo_url
            summary = r["notes"].replace("|", "\\|")
            out.append(f"| [`{slug}`]({r['target_subpath']}/) | `{kind}` | `{cluster_cell}` | [{repo}]({src_url}) | {summary} |")
        out.append("")

    out.append("---")
    out.append("")
    out.append("## Clusters")
    out.append("")
    out.append("Skills sharing a `cluster:` tag are intended to compose. See `_meta/clusters.md` for recommended pipelines.")
    out.append("")

    clusters: dict[str, list[dict]] = defaultdict(list)
    for r in imports:
        c = r["cluster"].strip()
        if c and c != "-":
            clusters[c].append(r)
    for cname in sorted(clusters):
        members = clusters[cname]
        out.append(f"### `{cname}`")
        out.append("")
        for m in sorted(members, key=lambda x: x["target_subpath"]):
            slug = Path(m["target_subpath"]).name
            out.append(f"- [`{slug}`]({m['target_subpath']}/) — {m['notes']}")
        out.append("")

    return "\n".join(out)


def main() -> None:
    imports, imported_targets = load_imports()
    native = list_native_skills(imported_targets)
    OUT.write_text(build_md(imports, native), encoding="utf-8")
    print(f"Wrote {OUT}")
    print(f"  imports: {len(imports)}")
    print(f"  native : {len(native)}")


if __name__ == "__main__":
    main()
