# Source — `x-to-markdown`

> Upstream tracking file. Do **not** edit `SKILL.md` here without recording the divergence in **Local modifications** below.

> ⚠️ **DANGER**: This skill depends on reverse-engineered / unofficial APIs. Authentication via browser session, cookies, or fragile endpoints. Upstream may break without notice. Use at your own risk.

## Upstream

| Field | Value |
|---|---|
| Repository | [JimLiu/baoyu-skills](https://github.com/JimLiu/baoyu-skills) |
| Skill path in repo | `/skills/baoyu-danger-x-to-markdown` |
| Canonical URL | [https://github.com/JimLiu/baoyu-skills/tree/main/skills/baoyu-danger-x-to-markdown](https://github.com/JimLiu/baoyu-skills/tree/main/skills/baoyu-danger-x-to-markdown) |
| Kind | `composite-danger` |
| Cluster | `extract` |
| Imported on | 2026-08-21 |
| License | see upstream `LICENSE` |

**Summary.** DANGER: reverse-engineered X/Twitter API to Markdown. Sibling: productivity/url-to-markdown.

## Related skills (same cluster)

- [url-to-markdown](../../productivity/url-to-markdown/) — Any-URL to Markdown via baoyu-fetch CLI; site adapters (X, YouTube, HN).
- [youtube-transcript](../../productivity/youtube-transcript/) — YouTube transcripts/subtitles/covers; chapters; speaker ID.

## Mounting into another project

This skill folder is self-contained. To use it elsewhere without copying:

```bash
# from the target project root
ln -s /absolute/path/to/skills/productivity/x-to-markdown/ ./.claude/skills/x-to-markdown
# or, on Windows (PowerShell, admin):
# New-Item -ItemType Junction -Path .\.claude\skills\x-to-markdown -Target E:\Project\Quantitative_Trading\skills\productivity/x-to-markdown
```

If your agent reads from `skill/<name>/SKILL.md`, only the `SKILL.md` is strictly required; `scripts/`, `references/`, and `assets/` are referenced by relative paths inside `SKILL.md`.

## Updating from upstream

1. Pull the latest from `https://github.com/JimLiu/baoyu-skills`.
2. Copy `/skills/baoyu-danger-x-to-markdown` over `skills/productivity/x-to-markdown/`, **preserving this `SOURCE.md`**.
3. Reconcile any entries listed under **Local modifications** below.
4. Update the `Imported on` date above and add a short note describing what changed.

## Local modifications

_(None at import time. Record edits here when they are made: date, reason, files touched.)_
