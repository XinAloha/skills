# Source — `good-question`

> Upstream tracking file. Do **not** edit `SKILL.md` here without recording the divergence in **Local modifications** below.

## Upstream

| Field | Value |
|---|---|
| Repository | [dontbesilent2025/dbskill](https://github.com/dontbesilent2025/dbskill) |
| Skill path in repo | `/skills/dbs-good-question` |
| Canonical URL | [https://github.com/dontbesilent2025/dbskill/tree/main/skills/dbs-good-question](https://github.com/dontbesilent2025/dbskill/tree/main/skills/dbs-good-question) |
| Kind | `atomic` |
| Cluster | `-` |
| Imported on | 2026-08-21 |
| License | see upstream `LICENSE` |

**Summary.** Turn fuzzy questions into criticizable, verifiable problem specs.

## Related skills (same cluster)

_(none in cluster)_

## Mounting into another project

This skill folder is self-contained. To use it elsewhere without copying:

```bash
# from the target project root
ln -s /absolute/path/to/skills/methodology/good-question/ ./.claude/skills/good-question
# or, on Windows (PowerShell, admin):
# New-Item -ItemType Junction -Path .\.claude\skills\good-question -Target E:\Project\Quantitative_Trading\skills\methodology/good-question
```

If your agent reads from `skill/<name>/SKILL.md`, only the `SKILL.md` is strictly required; `scripts/`, `references/`, and `assets/` are referenced by relative paths inside `SKILL.md`.

## Updating from upstream

1. Pull the latest from `https://github.com/dontbesilent2025/dbskill`.
2. Copy `/skills/dbs-good-question` over `skills/methodology/good-question/`, **preserving this `SOURCE.md`**.
3. Reconcile any entries listed under **Local modifications** below.
4. Update the `Imported on` date above and add a short note describing what changed.

## Local modifications

_(None at import time. Record edits here when they are made: date, reason, files touched.)_
