# Source — `skill-overseas-equity-factor-miner`

> Upstream tracking file. Do **not** edit `SKILL.md` here without recording the divergence in **Local modifications** below.

## Upstream

| Field | Value |
|---|---|
| Repository | [quantskills/skill-overseas-equity-factor-miner](https://github.com/quantskills/skill-overseas-equity-factor-miner) |
| Skill path in repo | `/` |
| Canonical URL | [https://github.com/quantskills/skill-overseas-equity-factor-miner](https://github.com/quantskills/skill-overseas-equity-factor-miner) |
| Kind | `composite` |
| Cluster | `-` |
| Imported on | 2026-08-21 |
| License | see upstream `LICENSE` |

**Summary.** 发现并以IC、衰减和换手率验证港美股横截面alpha因子。

## Related skills (same cluster)

_(none in cluster)_

## Mounting into another project

This skill folder is self-contained. To use it elsewhere without copying:

```bash
# from the target project root
ln -s /absolute/path/to/skills/quant/factors/skill-overseas-equity-factor-miner/ ./.claude/skills/skill-overseas-equity-factor-miner
# or, on Windows (PowerShell, admin):
# New-Item -ItemType Junction -Path .\.claude\skills\skill-overseas-equity-factor-miner -Target E:\Project\Quantitative_Trading\skills\quant/factors/skill-overseas-equity-factor-miner
```

If your agent reads from `skill/<name>/SKILL.md`, only the `SKILL.md` is strictly required; `scripts/`, `references/`, and `assets/` are referenced by relative paths inside `SKILL.md`.

## Updating from upstream

1. Pull the latest from `https://github.com/quantskills/skill-overseas-equity-factor-miner`.
2. Copy `/` over `skills/quant/factors/skill-overseas-equity-factor-miner/`, **preserving this `SOURCE.md`**.
3. Reconcile any entries listed under **Local modifications** below.
4. Update the `Imported on` date above and add a short note describing what changed.

## Local modifications

_(None at import time. Record edits here when they are made: date, reason, files touched.)_
