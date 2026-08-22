# Source — `skill-corporate-action-adjustment-auditor`

> Upstream tracking file. Do **not** edit `SKILL.md` here without recording the divergence in **Local modifications** below.

## Upstream

| Field | Value |
|---|---|
| Repository | [quantskills/skill-corporate-action-adjustment-auditor](https://github.com/quantskills/skill-corporate-action-adjustment-auditor) |
| Skill path in repo | `/` |
| Canonical URL | [https://github.com/quantskills/skill-corporate-action-adjustment-auditor](https://github.com/quantskills/skill-corporate-action-adjustment-auditor) |
| Kind | `composite` |
| Cluster | `-` |
| Imported on | 2026-08-21 |
| License | see upstream `LICENSE` |

**Summary.** 在研究或回测前审计原始与复权价格中的拆分和现金分红一致性。

## Related skills (same cluster)

_(none in cluster)_

## Mounting into another project

This skill folder is self-contained. To use it elsewhere without copying:

```bash
# from the target project root
ln -s /absolute/path/to/skills/quant/data/skill-corporate-action-adjustment-auditor/ ./.claude/skills/skill-corporate-action-adjustment-auditor
# or, on Windows (PowerShell, admin):
# New-Item -ItemType Junction -Path .\.claude\skills\skill-corporate-action-adjustment-auditor -Target E:\Project\Quantitative_Trading\skills\quant/data/skill-corporate-action-adjustment-auditor
```

If your agent reads from `skill/<name>/SKILL.md`, only the `SKILL.md` is strictly required; `scripts/`, `references/`, and `assets/` are referenced by relative paths inside `SKILL.md`.

## Updating from upstream

1. Pull the latest from `https://github.com/quantskills/skill-corporate-action-adjustment-auditor`.
2. Copy `/` over `skills/quant/data/skill-corporate-action-adjustment-auditor/`, **preserving this `SOURCE.md`**.
3. Reconcile any entries listed under **Local modifications** below.
4. Update the `Imported on` date above and add a short note describing what changed.

## Local modifications

_(None at import time. Record edits here when they are made: date, reason, files touched.)_
