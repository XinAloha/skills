# Source — `ai-check`

> Upstream tracking file. Do **not** edit `SKILL.md` here without recording the divergence in **Local modifications** below.

## Upstream

| Field | Value |
|---|---|
| Repository | [dontbesilent2025/dbskill](https://github.com/dontbesilent2025/dbskill) |
| Skill path in repo | `/skills/dbs-ai-check` |
| Canonical URL | [https://github.com/dontbesilent2025/dbskill/tree/main/skills/dbs-ai-check](https://github.com/dontbesilent2025/dbskill/tree/main/skills/dbs-ai-check) |
| Kind | `atomic` |
| Cluster | `humanizer` |
| Imported on | 2026-06-27 |
| License | see upstream `LICENSE` |

**Summary.** Detect AI-writing traces in Chinese text. Sibling: content/humanizer-zh (rewrites), content/format-markdown.

## Related skills (same cluster)

- [humanizer-zh](../../content/humanizer-zh/) — Chinese text de-AI-ification; rewrite to natural prose.
- [format-markdown](../../content/format-markdown/) — Format MD with frontmatter/titles/summaries/headings.

## Mounting into another project

This skill folder is self-contained. To use it elsewhere without copying:

```bash
# from the target project root
ln -s /absolute/path/to/skills/content/ai-check/ ./.claude/skills/ai-check
# or, on Windows (PowerShell, admin):
# New-Item -ItemType Junction -Path .\.claude\skills\ai-check -Target E:\Project\Quantitative_Trading\skills\content/ai-check
```

If your agent reads from `skill/<name>/SKILL.md`, only the `SKILL.md` is strictly required; `scripts/`, `references/`, and `assets/` are referenced by relative paths inside `SKILL.md`.

## Updating from upstream

1. Pull the latest from `https://github.com/dontbesilent2025/dbskill`.
2. Copy `/skills/dbs-ai-check` over `skills/content/ai-check/`, **preserving this `SOURCE.md`**.
3. Reconcile any entries listed under **Local modifications** below.
4. Update the `Imported on` date above and add a short note describing what changed.

## Local modifications

_(None at import time. Record edits here when they are made: date, reason, files touched.)_
