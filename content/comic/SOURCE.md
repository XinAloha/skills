# Source — `comic`

> Upstream tracking file. Do **not** edit `SKILL.md` here without recording the divergence in **Local modifications** below.

## Upstream

| Field | Value |
|---|---|
| Repository | [JimLiu/baoyu-skills](https://github.com/JimLiu/baoyu-skills) |
| Skill path in repo | `/skills/baoyu-comic` |
| Canonical URL | [https://github.com/JimLiu/baoyu-skills/tree/main/skills/baoyu-comic](https://github.com/JimLiu/baoyu-skills/tree/main/skills/baoyu-comic) |
| Kind | `composite` |
| Cluster | `visual` |
| Imported on | 2026-08-21 |
| License | see upstream `LICENSE` |

**Summary.** Knowledge comic creator (multi art-style, tones, panel layouts, batch image gen).

## Related skills (same cluster)

- [article-illustrator](../../content/article-illustrator/) — Article illustration planning + image prompts via Type x Style x Palette.
- [cover-image](../../content/cover-image/) — Article cover images: type x palette x rendering x text x mood.
- [infographic](../../content/infographic/) — Professional infographics with 21 layouts x 22 styles.

## Mounting into another project

This skill folder is self-contained. To use it elsewhere without copying:

```bash
# from the target project root
ln -s /absolute/path/to/skills/content/comic/ ./.claude/skills/comic
# or, on Windows (PowerShell, admin):
# New-Item -ItemType Junction -Path .\.claude\skills\comic -Target E:\Project\Quantitative_Trading\skills\content/comic
```

If your agent reads from `skill/<name>/SKILL.md`, only the `SKILL.md` is strictly required; `scripts/`, `references/`, and `assets/` are referenced by relative paths inside `SKILL.md`.

## Updating from upstream

1. Pull the latest from `https://github.com/JimLiu/baoyu-skills`.
2. Copy `/skills/baoyu-comic` over `skills/content/comic/`, **preserving this `SOURCE.md`**.
3. Reconcile any entries listed under **Local modifications** below.
4. Update the `Imported on` date above and add a short note describing what changed.

## Local modifications

_(None at import time. Record edits here when they are made: date, reason, files touched.)_
