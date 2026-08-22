# Source — `skill-factor-orthogonalize`

> Upstream tracking file. Do **not** edit `SKILL.md` here without recording the divergence in **Local modifications** below.

## Upstream

| Field | Value |
|---|---|
| Repository | [quantskills/skill-factor-orthogonalize](https://github.com/quantskills/skill-factor-orthogonalize) |
| Skill path in repo | `/` |
| Canonical URL | [https://github.com/quantskills/skill-factor-orthogonalize](https://github.com/quantskills/skill-factor-orthogonalize) |
| Kind | `composite` |
| Cluster | `-` |
| Imported on | 2026-08-21 |
| License | see upstream `LICENSE` |

**Summary.** 对截面因子进行逐日OLS正交化，并输出残差因子和暴露诊断。

## Related skills (same cluster)

_(none in cluster)_

## Mounting into another project

This skill folder is self-contained. To use it elsewhere without copying:

```bash
# from the target project root
ln -s /absolute/path/to/skills/quant/factors/skill-factor-orthogonalize/ ./.claude/skills/skill-factor-orthogonalize
# or, on Windows (PowerShell, admin):
# New-Item -ItemType Junction -Path .\.claude\skills\skill-factor-orthogonalize -Target E:\Project\Quantitative_Trading\skills\quant/factors/skill-factor-orthogonalize
```

If your agent reads from `skill/<name>/SKILL.md`, only the `SKILL.md` is strictly required; `scripts/`, `references/`, and `assets/` are referenced by relative paths inside `SKILL.md`.

## Updating from upstream

1. Pull the latest from `https://github.com/quantskills/skill-factor-orthogonalize`.
2. Copy `/` over `skills/quant/factors/skill-factor-orthogonalize/`, **preserving this `SOURCE.md`**.
3. Reconcile any entries listed under **Local modifications** below.
4. Update the `Imported on` date above and add a short note describing what changed.

## Local modifications

_(None at import time. Record edits here when they are made: date, reason, files touched.)_
