# Source — `dbs-update`

> Upstream tracking file. Do **not** edit `SKILL.md` here without recording the divergence in **Local modifications** below.

## Upstream

| Field | Value |
|---|---|
| Repository | [dontbesilent2025/dbskill](https://github.com/dontbesilent2025/dbskill) |
| Skill path in repo | `/skills/dbs-update` |
| Canonical URL | [https://github.com/dontbesilent2025/dbskill/tree/main/skills/dbs-update](https://github.com/dontbesilent2025/dbskill/tree/main/skills/dbs-update) |
| Kind | `atomic` |
| Cluster | `-` |
| Imported on | 2026-08-21 |
| License | see upstream `LICENSE` |

**Summary.** Update the official dbskill suite while preserving other skills and user archives.

## Related skills (same cluster)

_(none in cluster)_

## Mounting into another project

This skill folder is self-contained. To use it elsewhere without copying:

```bash
# from the target project root
ln -s /absolute/path/to/skills/meta/dbs-update/ ./.claude/skills/dbs-update
# or, on Windows (PowerShell, admin):
# New-Item -ItemType Junction -Path .\.claude\skills\dbs-update -Target E:\Project\Quantitative_Trading\skills\meta/dbs-update
```

If your agent reads from `skill/<name>/SKILL.md`, only the `SKILL.md` is strictly required; `scripts/`, `references/`, and `assets/` are referenced by relative paths inside `SKILL.md`.

## Updating from upstream

1. Pull the latest from `https://github.com/dontbesilent2025/dbskill`.
2. Copy `/skills/dbs-update` over `skills/meta/dbs-update/`, **preserving this `SOURCE.md`**.
3. Reconcile any entries listed under **Local modifications** below.
4. Update the `Imported on` date above and add a short note describing what changed.

## Local modifications

_(None at import time. Record edits here when they are made: date, reason, files touched.)_
