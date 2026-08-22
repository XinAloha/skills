# Source — `skill-factor-decay`

> Upstream tracking file. Do **not** edit `SKILL.md` here without recording the divergence in **Local modifications** below.

## Upstream

| Field | Value |
|---|---|
| Repository | [quantskills/skill-factor-decay](https://github.com/quantskills/skill-factor-decay) |
| Skill path in repo | `/` |
| Canonical URL | [https://github.com/quantskills/skill-factor-decay](https://github.com/quantskills/skill-factor-decay) |
| Kind | `composite` |
| Cluster | `-` |
| Imported on | 2026-08-21 |
| License | see upstream `LICENSE` |

**Summary.** 分析多期限Rank IC、换手和分组收益的衰减，并估计半衰期。

## Related skills (same cluster)

_(none in cluster)_

## Mounting into another project

This skill folder is self-contained. To use it elsewhere without copying:

```bash
# from the target project root
ln -s /absolute/path/to/skills/quant/validation/skill-factor-decay/ ./.claude/skills/skill-factor-decay
# or, on Windows (PowerShell, admin):
# New-Item -ItemType Junction -Path .\.claude\skills\skill-factor-decay -Target E:\Project\Quantitative_Trading\skills\quant/validation/skill-factor-decay
```

If your agent reads from `skill/<name>/SKILL.md`, only the `SKILL.md` is strictly required; `scripts/`, `references/`, and `assets/` are referenced by relative paths inside `SKILL.md`.

## Updating from upstream

1. Pull the latest from `https://github.com/quantskills/skill-factor-decay`.
2. Copy `/` over `skills/quant/validation/skill-factor-decay/`, **preserving this `SOURCE.md`**.
3. Reconcile any entries listed under **Local modifications** below.
4. Update the `Imported on` date above and add a short note describing what changed.

## Local modifications

_(None at import time. Record edits here when they are made: date, reason, files touched.)_
