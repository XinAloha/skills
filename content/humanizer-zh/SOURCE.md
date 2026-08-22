# Source — `humanizer-zh`

> Upstream tracking file. Do **not** edit `SKILL.md` here without recording the divergence in **Local modifications** below.

## Upstream

| Field | Value |
|---|---|
| Repository | [op7418/Humanizer-zh](https://github.com/op7418/Humanizer-zh) |
| Skill path in repo | `/` |
| Canonical URL | [https://github.com/op7418/Humanizer-zh](https://github.com/op7418/Humanizer-zh) |
| Kind | `atomic` |
| Cluster | `humanizer` |
| Imported on | 2026-08-21 |
| License | see upstream `LICENSE` |

**Summary.** Chinese text de-AI-ification; rewrite to natural prose. Sibling: content/ai-check (detects), content/format-markdown (formats).

## Related skills (same cluster)

- [format-markdown](../../content/format-markdown/) — Format MD with frontmatter/titles/summaries/headings.
- [ai-check](../../content/ai-check/) — Detect AI-writing traces in Chinese text.

## Mounting into another project

This skill folder is self-contained. To use it elsewhere without copying:

```bash
# from the target project root
ln -s /absolute/path/to/skills/content/humanizer-zh/ ./.claude/skills/humanizer-zh
# or, on Windows (PowerShell, admin):
# New-Item -ItemType Junction -Path .\.claude\skills\humanizer-zh -Target E:\Project\Quantitative_Trading\skills\content/humanizer-zh
```

If your agent reads from `skill/<name>/SKILL.md`, only the `SKILL.md` is strictly required; `scripts/`, `references/`, and `assets/` are referenced by relative paths inside `SKILL.md`.

## Updating from upstream

1. Pull the latest from `https://github.com/op7418/Humanizer-zh`.
2. Copy `/` over `skills/content/humanizer-zh/`, **preserving this `SOURCE.md`**.
3. Reconcile any entries listed under **Local modifications** below.
4. Update the `Imported on` date above and add a short note describing what changed.

## Local modifications

_(None at import time. Record edits here when they are made: date, reason, files touched.)_
