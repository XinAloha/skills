# Source — `guizang-ppt`

> Upstream tracking file. Do **not** edit `SKILL.md` here without recording the divergence in **Local modifications** below.

## Upstream

| Field | Value |
|---|---|
| Repository | [op7418/guizang-ppt-skill](https://github.com/op7418/guizang-ppt-skill) |
| Skill path in repo | `/` |
| Canonical URL | [https://github.com/op7418/guizang-ppt-skill](https://github.com/op7418/guizang-ppt-skill) |
| Kind | `composite` |
| Cluster | `slide` |
| Imported on | 2026-08-21 |
| License | see upstream `LICENSE` |

**Summary.** Horizontal swipe web PPT as single HTML file (WebGL bg, chapter covers, big-number data pages). Sibling: content/slide-deck-baoyu.

## Related skills (same cluster)

- [slide-deck-baoyu](../../content/slide-deck-baoyu/) — Slide deck images from content.

## Mounting into another project

This skill folder is self-contained. To use it elsewhere without copying:

```bash
# from the target project root
ln -s /absolute/path/to/skills/content/guizang-ppt/ ./.claude/skills/guizang-ppt
# or, on Windows (PowerShell, admin):
# New-Item -ItemType Junction -Path .\.claude\skills\guizang-ppt -Target E:\Project\Quantitative_Trading\skills\content/guizang-ppt
```

If your agent reads from `skill/<name>/SKILL.md`, only the `SKILL.md` is strictly required; `scripts/`, `references/`, and `assets/` are referenced by relative paths inside `SKILL.md`.

## Updating from upstream

1. Pull the latest from `https://github.com/op7418/guizang-ppt-skill`.
2. Copy `/` over `skills/content/guizang-ppt/`, **preserving this `SOURCE.md`**.
3. Reconcile any entries listed under **Local modifications** below.
4. Update the `Imported on` date above and add a short note describing what changed.

## Local modifications

_(None at import time. Record edits here when they are made: date, reason, files touched.)_
