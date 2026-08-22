# Source — `skill-quant-factor-skill-factory`

> Upstream tracking file. Do **not** edit `SKILL.md` here without recording the divergence in **Local modifications** below.

## Upstream

| Field | Value |
|---|---|
| Repository | [quantskills/skill-quant-factor-skill-factory](https://github.com/quantskills/skill-quant-factor-skill-factory) |
| Skill path in repo | `/` |
| Canonical URL | [https://github.com/quantskills/skill-quant-factor-skill-factory](https://github.com/quantskills/skill-quant-factor-skill-factory) |
| Kind | `composite` |
| Cluster | `-` |
| Imported on | 2026-08-21 |
| License | see upstream `LICENSE` |

**Summary.** 批量生成、验证并打包框架中立的 OHLCV 因子技能。

## Related skills (same cluster)

_(none in cluster)_

## Mounting into another project

This skill folder is self-contained. To use it elsewhere without copying:

```bash
# from the target project root
ln -s /absolute/path/to/skills/quant/infra/skill-quant-factor-skill-factory/ ./.claude/skills/skill-quant-factor-skill-factory
# or, on Windows (PowerShell, admin):
# New-Item -ItemType Junction -Path .\.claude\skills\skill-quant-factor-skill-factory -Target E:\Project\Quantitative_Trading\skills\quant/infra/skill-quant-factor-skill-factory
```

If your agent reads from `skill/<name>/SKILL.md`, only the `SKILL.md` is strictly required; `scripts/`, `references/`, and `assets/` are referenced by relative paths inside `SKILL.md`.

## Updating from upstream

1. Pull the latest from `https://github.com/quantskills/skill-quant-factor-skill-factory`.
2. Copy `/` over `skills/quant/infra/skill-quant-factor-skill-factory/`, **preserving this `SOURCE.md`**.
3. Reconcile any entries listed under **Local modifications** below.
4. Update the `Imported on` date above and add a short note describing what changed.

## Local modifications

_(None at import time. Record edits here when they are made: date, reason, files touched.)_
