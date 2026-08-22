# Source — `skill-cleaner`

> Upstream tracking file. Do **not** edit `SKILL.md` here without recording the divergence in **Local modifications** below.

## Upstream

| Field | Value |
|---|---|
| Repository | [dontbesilent2025/dbskill](https://github.com/dontbesilent2025/dbskill) |
| Skill path in repo | `/skills/dbs-skill-cleaner` |
| Canonical URL | [https://github.com/dontbesilent2025/dbskill/tree/main/skills/dbs-skill-cleaner](https://github.com/dontbesilent2025/dbskill/tree/main/skills/dbs-skill-cleaner) |
| Kind | `composite` |
| Cluster | `-` |
| Imported on | 2026-08-21 |
| License | see upstream `LICENSE` |

**Summary.** Scan local skills for ad/stealth-commercial intent, task hijacking, suspicious external calls, sensitive-data reads; report-only by default.

## Related skills (same cluster)

_(none in cluster)_

## Mounting into another project

This skill folder is self-contained. To use it elsewhere without copying:

```bash
# from the target project root
ln -s /absolute/path/to/skills/meta/skill-cleaner/ ./.claude/skills/skill-cleaner
# or, on Windows (PowerShell, admin):
# New-Item -ItemType Junction -Path .\.claude\skills\skill-cleaner -Target E:\Project\Quantitative_Trading\skills\meta/skill-cleaner
```

If your agent reads from `skill/<name>/SKILL.md`, only the `SKILL.md` is strictly required; `scripts/`, `references/`, and `assets/` are referenced by relative paths inside `SKILL.md`.

## Updating from upstream

1. Pull the latest from `https://github.com/dontbesilent2025/dbskill`.
2. Copy `/skills/dbs-skill-cleaner` over `skills/meta/skill-cleaner/`, **preserving this `SOURCE.md`**.
3. Reconcile any entries listed under **Local modifications** below.
4. Update the `Imported on` date above and add a short note describing what changed.

## Local modifications

_(None at import time. Record edits here when they are made: date, reason, files touched.)_
