# Source — `youtube-transcript`

> Upstream tracking file. Do **not** edit `SKILL.md` here without recording the divergence in **Local modifications** below.

## Upstream

| Field | Value |
|---|---|
| Repository | [JimLiu/baoyu-skills](https://github.com/JimLiu/baoyu-skills) |
| Skill path in repo | `/skills/baoyu-youtube-transcript` |
| Canonical URL | [https://github.com/JimLiu/baoyu-skills/tree/main/skills/baoyu-youtube-transcript](https://github.com/JimLiu/baoyu-skills/tree/main/skills/baoyu-youtube-transcript) |
| Kind | `composite` |
| Cluster | `extract` |
| Imported on | 2026-06-27 |
| License | see upstream `LICENSE` |

**Summary.** YouTube transcripts/subtitles/covers; chapters; speaker ID.

## Related skills (same cluster)

- [x-to-markdown](../../productivity/x-to-markdown/) — DANGER: reverse-engineered X/Twitter API to Markdown.
- [url-to-markdown](../../productivity/url-to-markdown/) — Any-URL to Markdown via baoyu-fetch CLI; site adapters (X, YouTube, HN).

## Mounting into another project

This skill folder is self-contained. To use it elsewhere without copying:

```bash
# from the target project root
ln -s /absolute/path/to/skills/productivity/youtube-transcript/ ./.claude/skills/youtube-transcript
# or, on Windows (PowerShell, admin):
# New-Item -ItemType Junction -Path .\.claude\skills\youtube-transcript -Target E:\Project\Quantitative_Trading\skills\productivity/youtube-transcript
```

If your agent reads from `skill/<name>/SKILL.md`, only the `SKILL.md` is strictly required; `scripts/`, `references/`, and `assets/` are referenced by relative paths inside `SKILL.md`.

## Updating from upstream

1. Pull the latest from `https://github.com/JimLiu/baoyu-skills`.
2. Copy `/skills/baoyu-youtube-transcript` over `skills/productivity/youtube-transcript/`, **preserving this `SOURCE.md`**.
3. Reconcile any entries listed under **Local modifications** below.
4. Update the `Imported on` date above and add a short note describing what changed.

## Local modifications

_(None at import time. Record edits here when they are made: date, reason, files touched.)_
