# Source — `skill-a-share-pit-fundamental-vintage-builder`

> Upstream tracking file. Do **not** edit `SKILL.md` here without recording the divergence in **Local modifications** below.

## Upstream

| Field | Value |
|---|---|
| Repository | [quantskills/skill-a-share-pit-fundamental-vintage-builder](https://github.com/quantskills/skill-a-share-pit-fundamental-vintage-builder) |
| Skill path in repo | `/` |
| Canonical URL | [https://github.com/quantskills/skill-a-share-pit-fundamental-vintage-builder](https://github.com/quantskills/skill-a-share-pit-fundamental-vintage-builder) |
| Kind | `composite` |
| Cluster | `-` |
| Imported on | 2026-08-21 |
| License | see upstream `LICENSE` |

**Summary.** 按披露可见时点构建并审计 A 股财务数据，避免使用后续重述信息。

## Related skills (same cluster)

_(none in cluster)_

## Mounting into another project

This skill folder is self-contained. To use it elsewhere without copying:

```bash
# from the target project root
ln -s /absolute/path/to/skills/quant/data/skill-a-share-pit-fundamental-vintage-builder/ ./.claude/skills/skill-a-share-pit-fundamental-vintage-builder
# or, on Windows (PowerShell, admin):
# New-Item -ItemType Junction -Path .\.claude\skills\skill-a-share-pit-fundamental-vintage-builder -Target E:\Project\Quantitative_Trading\skills\quant/data/skill-a-share-pit-fundamental-vintage-builder
```

If your agent reads from `skill/<name>/SKILL.md`, only the `SKILL.md` is strictly required; `scripts/`, `references/`, and `assets/` are referenced by relative paths inside `SKILL.md`.

## Updating from upstream

1. Pull the latest from `https://github.com/quantskills/skill-a-share-pit-fundamental-vintage-builder`.
2. Copy `/` over `skills/quant/data/skill-a-share-pit-fundamental-vintage-builder/`, **preserving this `SOURCE.md`**.
3. Reconcile any entries listed under **Local modifications** below.
4. Update the `Imported on` date above and add a short note describing what changed.

## Local modifications

_(None at import time. Record edits here when they are made: date, reason, files touched.)_
