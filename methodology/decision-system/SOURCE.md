# Source — `decision-system`

> Upstream tracking file. Do **not** edit `SKILL.md` here without recording the divergence in **Local modifications** below.

## Upstream

| Field | Value |
|---|---|
| Repository | [dontbesilent2025/dbskill](https://github.com/dontbesilent2025/dbskill) |
| Skill path in repo | `/skills/dbs-decision` |
| Canonical URL | [https://github.com/dontbesilent2025/dbskill/tree/main/skills/dbs-decision](https://github.com/dontbesilent2025/dbskill/tree/main/skills/dbs-decision) |
| Kind | `atomic` |
| Cluster | `-` |
| Imported on | 2026-08-21 |
| License | see upstream `LICENSE` |

**Summary.** Personal decision system: 4-layer local Markdown knowledge engineering.

## Related skills (same cluster)

_(none in cluster)_

## Mounting into another project

This skill folder is self-contained. To use it elsewhere without copying:

```bash
# from the target project root
ln -s /absolute/path/to/skills/methodology/decision-system/ ./.claude/skills/decision-system
# or, on Windows (PowerShell, admin):
# New-Item -ItemType Junction -Path .\.claude\skills\decision-system -Target E:\Project\Quantitative_Trading\skills\methodology/decision-system
```

If your agent reads from `skill/<name>/SKILL.md`, only the `SKILL.md` is strictly required; `scripts/`, `references/`, and `assets/` are referenced by relative paths inside `SKILL.md`.

## Updating from upstream

1. Pull the latest from `https://github.com/dontbesilent2025/dbskill`.
2. Copy `/skills/dbs-decision` over `skills/methodology/decision-system/`, **preserving this `SOURCE.md`**.
3. Reconcile any entries listed under **Local modifications** below.
4. Update the `Imported on` date above and add a short note describing what changed.

## Local modifications

_(None at import time. Record edits here when they are made: date, reason, files touched.)_
