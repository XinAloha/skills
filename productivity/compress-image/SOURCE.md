# Source — `compress-image`

> Upstream tracking file. Do **not** edit `SKILL.md` here without recording the divergence in **Local modifications** below.

## Upstream

| Field | Value |
|---|---|
| Repository | [JimLiu/baoyu-skills](https://github.com/JimLiu/baoyu-skills) |
| Skill path in repo | `/skills/baoyu-compress-image` |
| Canonical URL | [https://github.com/JimLiu/baoyu-skills/tree/main/skills/baoyu-compress-image](https://github.com/JimLiu/baoyu-skills/tree/main/skills/baoyu-compress-image) |
| Kind | `composite` |
| Cluster | `-` |
| Imported on | 2026-08-21 |
| License | see upstream `LICENSE` |

**Summary.** WebP/PNG compression via sips/cwebp/ImageMagick/Sharp.

## Related skills (same cluster)

_(none in cluster)_

## Mounting into another project

This skill folder is self-contained. To use it elsewhere without copying:

```bash
# from the target project root
ln -s /absolute/path/to/skills/productivity/compress-image/ ./.claude/skills/compress-image
# or, on Windows (PowerShell, admin):
# New-Item -ItemType Junction -Path .\.claude\skills\compress-image -Target E:\Project\Quantitative_Trading\skills\productivity/compress-image
```

If your agent reads from `skill/<name>/SKILL.md`, only the `SKILL.md` is strictly required; `scripts/`, `references/`, and `assets/` are referenced by relative paths inside `SKILL.md`.

## Updating from upstream

1. Pull the latest from `https://github.com/JimLiu/baoyu-skills`.
2. Copy `/skills/baoyu-compress-image` over `skills/productivity/compress-image/`, **preserving this `SOURCE.md`**.
3. Reconcile any entries listed under **Local modifications** below.
4. Update the `Imported on` date above and add a short note describing what changed.

## Local modifications

_(None at import time. Record edits here when they are made: date, reason, files touched.)_
