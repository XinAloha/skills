# Source — `notebooklm`

> Upstream tracking file. Do **not** edit `SKILL.md` here without recording the divergence in **Local modifications** below.

## Upstream

| Field | Value |
|---|---|
| Repository | [PleasePrompto/notebooklm-skill](https://github.com/PleasePrompto/notebooklm-skill) |
| Skill path in repo | `/` |
| Canonical URL | [https://github.com/PleasePrompto/notebooklm-skill](https://github.com/PleasePrompto/notebooklm-skill) |
| Kind | `composite` |
| Cluster | `-` |
| Imported on | 2026-08-21 |
| License | see upstream `LICENSE` |

**Summary.** Query Google NotebookLM from agent for citation-backed answers; browser automation.

## Related skills (same cluster)

_(none in cluster)_

## Mounting into another project

This skill folder is self-contained. To use it elsewhere without copying:

```bash
# from the target project root
ln -s /absolute/path/to/skills/productivity/notebooklm/ ./.claude/skills/notebooklm
# or, on Windows (PowerShell, admin):
# New-Item -ItemType Junction -Path .\.claude\skills\notebooklm -Target E:\Project\Quantitative_Trading\skills\productivity/notebooklm
```

If your agent reads from `skill/<name>/SKILL.md`, only the `SKILL.md` is strictly required; `scripts/`, `references/`, and `assets/` are referenced by relative paths inside `SKILL.md`.

## Updating from upstream

1. Pull the latest from `https://github.com/PleasePrompto/notebooklm-skill`.
2. Copy `/` over `skills/productivity/notebooklm/`, **preserving this `SOURCE.md`**.
3. Reconcile any entries listed under **Local modifications** below.
4. Update the `Imported on` date above and add a short note describing what changed.

## Local modifications

_(None at import time. Record edits here when they are made: date, reason, files touched.)_
