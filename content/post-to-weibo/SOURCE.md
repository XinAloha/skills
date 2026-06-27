# Source — `post-to-weibo`

> Upstream tracking file. Do **not** edit `SKILL.md` here without recording the divergence in **Local modifications** below.

## Upstream

| Field | Value |
|---|---|
| Repository | [JimLiu/baoyu-skills](https://github.com/JimLiu/baoyu-skills) |
| Skill path in repo | `/skills/baoyu-post-to-weibo` |
| Canonical URL | [https://github.com/JimLiu/baoyu-skills/tree/main/skills/baoyu-post-to-weibo](https://github.com/JimLiu/baoyu-skills/tree/main/skills/baoyu-post-to-weibo) |
| Kind | `composite` |
| Cluster | `publish` |
| Imported on | 2026-06-27 |
| License | see upstream `LICENSE` |

**Summary.** Post to Weibo via Chrome CDP; supports articles.

## Related skills (same cluster)

- [markdown-to-html](../../content/markdown-to-html/) — Markdown to styled HTML (WeChat-compatible themes, code highlight, math, Mermaid, PlantUML, footnotes, citations).
- [post-to-wechat](../../content/post-to-wechat/) — Post to WeChat Official Account via API or Chrome CDP.
- [post-to-x](../../content/post-to-x/) — Post to X/Twitter via Chrome extension, Computer Use, or CDP.

## Mounting into another project

This skill folder is self-contained. To use it elsewhere without copying:

```bash
# from the target project root
ln -s /absolute/path/to/skills/content/post-to-weibo/ ./.claude/skills/post-to-weibo
# or, on Windows (PowerShell, admin):
# New-Item -ItemType Junction -Path .\.claude\skills\post-to-weibo -Target E:\Project\Quantitative_Trading\skills\content/post-to-weibo
```

If your agent reads from `skill/<name>/SKILL.md`, only the `SKILL.md` is strictly required; `scripts/`, `references/`, and `assets/` are referenced by relative paths inside `SKILL.md`.

## Updating from upstream

1. Pull the latest from `https://github.com/JimLiu/baoyu-skills`.
2. Copy `/skills/baoyu-post-to-weibo` over `skills/content/post-to-weibo/`, **preserving this `SOURCE.md`**.
3. Reconcile any entries listed under **Local modifications** below.
4. Update the `Imported on` date above and add a short note describing what changed.

## Local modifications

_(None at import time. Record edits here when they are made: date, reason, files touched.)_
