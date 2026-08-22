# Source — `skill-quant-research`

> Upstream tracking file. Do **not** edit `SKILL.md` here without recording the divergence in **Local modifications** below.

## Upstream

| Field | Value |
|---|---|
| Repository | [quantskills/skill-quant-research](https://github.com/quantskills/skill-quant-research) |
| Skill path in repo | `/` |
| Canonical URL | [https://github.com/quantskills/skill-quant-research](https://github.com/quantskills/skill-quant-research) |
| Kind | `composite` |
| Cluster | `-` |
| Imported on | 2026-08-21 |
| License | see upstream `LICENSE` |

**Summary.** 指导量化研究、回测设计和统计验证工作流。

## Related skills (same cluster)

_(none in cluster)_

## Mounting into another project

This skill folder is self-contained. To use it elsewhere without copying:

```bash
# from the target project root
ln -s /absolute/path/to/skills/quant/models/skill-quant-research/ ./.claude/skills/skill-quant-research
# or, on Windows (PowerShell, admin):
# New-Item -ItemType Junction -Path .\.claude\skills\skill-quant-research -Target E:\Project\Quantitative_Trading\skills\quant/models/skill-quant-research
```

If your agent reads from `skill/<name>/SKILL.md`, only the `SKILL.md` is strictly required; `scripts/`, `references/`, and `assets/` are referenced by relative paths inside `SKILL.md`.

## Updating from upstream

1. Pull the latest from `https://github.com/quantskills/skill-quant-research`.
2. Copy `/` over `skills/quant/models/skill-quant-research/`, **preserving this `SOURCE.md`**.
3. Reconcile any entries listed under **Local modifications** below.
4. Update the `Imported on` date above and add a short note describing what changed.

## Local modifications

_(None at import time. Record edits here when they are made: date, reason, files touched.)_
