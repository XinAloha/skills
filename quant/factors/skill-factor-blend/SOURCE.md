# Source — `skill-factor-blend`

> Upstream tracking file. Do **not** edit `SKILL.md` here without recording the divergence in **Local modifications** below.

## Upstream

| Field | Value |
|---|---|
| Repository | [quantskills/skill-factor-blend](https://github.com/quantskills/skill-factor-blend) |
| Skill path in repo | `/` |
| Canonical URL | [https://github.com/quantskills/skill-factor-blend](https://github.com/quantskills/skill-factor-blend) |
| Kind | `composite` |
| Cluster | `-` |
| Imported on | 2026-08-21 |
| License | see upstream `LICENSE` |

**Summary.** 将多个因子信号去冗余、加权并合成为复合信号。

## Related skills (same cluster)

_(none in cluster)_

## Mounting into another project

This skill folder is self-contained. To use it elsewhere without copying:

```bash
# from the target project root
ln -s /absolute/path/to/skills/quant/factors/skill-factor-blend/ ./.claude/skills/skill-factor-blend
# or, on Windows (PowerShell, admin):
# New-Item -ItemType Junction -Path .\.claude\skills\skill-factor-blend -Target E:\Project\Quantitative_Trading\skills\quant/factors/skill-factor-blend
```

If your agent reads from `skill/<name>/SKILL.md`, only the `SKILL.md` is strictly required; `scripts/`, `references/`, and `assets/` are referenced by relative paths inside `SKILL.md`.

## Updating from upstream

1. Pull the latest from `https://github.com/quantskills/skill-factor-blend`.
2. Copy `/` over `skills/quant/factors/skill-factor-blend/`, **preserving this `SOURCE.md`**.
3. Reconcile any entries listed under **Local modifications** below.
4. Update the `Imported on` date above and add a short note describing what changed.

## Local modifications

_(None at import time. Record edits here when they are made: date, reason, files touched.)_
