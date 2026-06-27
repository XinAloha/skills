# Source — `format-markdown`

> Upstream tracking file. Do **not** edit `SKILL.md` here without recording the divergence in **Local modifications** below.

## Upstream

| Field | Value |
|---|---|
| Repository | [JimLiu/baoyu-skills](https://github.com/JimLiu/baoyu-skills) |
| Skill path in repo | `/skills/baoyu-format-markdown` |
| Canonical URL | [https://github.com/JimLiu/baoyu-skills/tree/main/skills/baoyu-format-markdown](https://github.com/JimLiu/baoyu-skills/tree/main/skills/baoyu-format-markdown) |
| Kind | `composite` |
| Cluster | `humanizer` |
| Imported on | 2026-06-27 |
| License | see upstream `LICENSE` |

**Summary.** Format MD with frontmatter/titles/summaries/headings. Sibling: content/humanizer-zh, content/ai-check.

## Related skills (same cluster)

- [humanizer-zh](../../content/humanizer-zh/) — Chinese text de-AI-ification; rewrite to natural prose.
- [ai-check](../../content/ai-check/) — Detect AI-writing traces in Chinese text.

## Mounting into another project

This skill folder is self-contained. To use it elsewhere without copying:

```bash
# from the target project root
ln -s /absolute/path/to/skills/content/format-markdown/ ./.claude/skills/format-markdown
# or, on Windows (PowerShell, admin):
# New-Item -ItemType Junction -Path .\.claude\skills\format-markdown -Target E:\Project\Quantitative_Trading\skills\content/format-markdown
```

If your agent reads from `skill/<name>/SKILL.md`, only the `SKILL.md` is strictly required; `scripts/`, `references/`, and `assets/` are referenced by relative paths inside `SKILL.md`.

## Updating from upstream

1. Pull the latest from `https://github.com/JimLiu/baoyu-skills`.
2. Copy `/skills/baoyu-format-markdown` over `skills/content/format-markdown/`, **preserving this `SOURCE.md`**.
3. Reconcile any entries listed under **Local modifications** below.
4. Update the `Imported on` date above and add a short note describing what changed.

## Local modifications

_(None at import time. Record edits here when they are made: date, reason, files touched.)_
