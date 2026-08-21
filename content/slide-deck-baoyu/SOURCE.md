# Source — `slide-deck-baoyu`

> Upstream tracking file. Do **not** edit `SKILL.md` here without recording the divergence in **Local modifications** below.

## Upstream

| Field | Value |
|---|---|
| Repository | [JimLiu/baoyu-skills](https://github.com/JimLiu/baoyu-skills) |
| Skill path in repo | `/skills/baoyu-slide-deck` |
| Canonical URL | [https://github.com/JimLiu/baoyu-skills/tree/main/skills/baoyu-slide-deck](https://github.com/JimLiu/baoyu-skills/tree/main/skills/baoyu-slide-deck) |
| Kind | `composite` |
| Cluster | `slide` |
| Imported on | 2026-08-21 |
| License | see upstream `LICENSE` |

**Summary.** Slide deck images from content. Sibling: content/guizang-ppt.

## Related skills (same cluster)

- [guizang-ppt](../../content/guizang-ppt/) — Horizontal swipe web PPT as single HTML file (WebGL bg, chapter covers, big-number data pages).

## Mounting into another project

This skill folder is self-contained. To use it elsewhere without copying:

```bash
# from the target project root
ln -s /absolute/path/to/skills/content/slide-deck-baoyu/ ./.claude/skills/slide-deck-baoyu
# or, on Windows (PowerShell, admin):
# New-Item -ItemType Junction -Path .\.claude\skills\slide-deck-baoyu -Target E:\Project\Quantitative_Trading\skills\content/slide-deck-baoyu
```

If your agent reads from `skill/<name>/SKILL.md`, only the `SKILL.md` is strictly required; `scripts/`, `references/`, and `assets/` are referenced by relative paths inside `SKILL.md`.

## Updating from upstream

1. Pull the latest from `https://github.com/JimLiu/baoyu-skills`.
2. Copy `/skills/baoyu-slide-deck` over `skills/content/slide-deck-baoyu/`, **preserving this `SOURCE.md`**.
3. Reconcile any entries listed under **Local modifications** below.
4. Update the `Imported on` date above and add a short note describing what changed.

## Local modifications

_(None at import time. Record edits here when they are made: date, reason, files touched.)_
