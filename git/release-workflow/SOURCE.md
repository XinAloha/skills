# Source — `release-workflow`

> Upstream tracking file. Do **not** edit `SKILL.md` here without recording the divergence in **Local modifications** below.

## Upstream

| Field | Value |
|---|---|
| Repository | [JimLiu/baoyu-skills](https://github.com/JimLiu/baoyu-skills) |
| Skill path in repo | `/.claude/skills/release-skills` |
| Canonical URL | [https://github.com/JimLiu/baoyu-skills/tree/main/.claude/skills/release-skills](https://github.com/JimLiu/baoyu-skills/tree/main/.claude/skills/release-skills) |
| Kind | `atomic` |
| Cluster | `-` |
| Imported on | 2026-08-21 |
| License | see upstream `LICENSE` |

**Summary.** Universal release workflow (Node/Python/Rust/Claude plugin/GitHub Releases/tags/backfill).

## Related skills (same cluster)

_(none in cluster)_

## Mounting into another project

This skill folder is self-contained. To use it elsewhere without copying:

```bash
# from the target project root
ln -s /absolute/path/to/skills/git/release-workflow/ ./.claude/skills/release-workflow
# or, on Windows (PowerShell, admin):
# New-Item -ItemType Junction -Path .\.claude\skills\release-workflow -Target E:\Project\Quantitative_Trading\skills\git/release-workflow
```

If your agent reads from `skill/<name>/SKILL.md`, only the `SKILL.md` is strictly required; `scripts/`, `references/`, and `assets/` are referenced by relative paths inside `SKILL.md`.

## Updating from upstream

1. Pull the latest from `https://github.com/JimLiu/baoyu-skills`.
2. Copy `/.claude/skills/release-skills` over `skills/git/release-workflow/`, **preserving this `SOURCE.md`**.
3. Reconcile any entries listed under **Local modifications** below.
4. Update the `Imported on` date above and add a short note describing what changed.

## Local modifications

_(None at import time. Record edits here when they are made: date, reason, files touched.)_
