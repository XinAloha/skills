# Source — `translate`

> Upstream tracking file. Do **not** edit `SKILL.md` here without recording the divergence in **Local modifications** below.

## Upstream

| Field | Value |
|---|---|
| Repository | [JimLiu/baoyu-skills](https://github.com/JimLiu/baoyu-skills) |
| Skill path in repo | `/skills/baoyu-translate` |
| Canonical URL | [https://github.com/JimLiu/baoyu-skills/tree/main/skills/baoyu-translate](https://github.com/JimLiu/baoyu-skills/tree/main/skills/baoyu-translate) |
| Kind | `composite` |
| Cluster | `-` |
| Imported on | 2026-06-27 |
| License | see upstream `LICENSE` |

**Summary.** Three-mode translation: quick/normal/refined (with subagent polish).

## Related skills (same cluster)

_(none in cluster)_

## Mounting into another project

This skill folder is self-contained. To use it elsewhere without copying:

```bash
# from the target project root
ln -s /absolute/path/to/skills/content/translate/ ./.claude/skills/translate
# or, on Windows (PowerShell, admin):
# New-Item -ItemType Junction -Path .\.claude\skills\translate -Target E:\Project\Quantitative_Trading\skills\content/translate
```

If your agent reads from `skill/<name>/SKILL.md`, only the `SKILL.md` is strictly required; `scripts/`, `references/`, and `assets/` are referenced by relative paths inside `SKILL.md`.

## Updating from upstream

1. Pull the latest from `https://github.com/JimLiu/baoyu-skills`.
2. Copy `/skills/baoyu-translate` over `skills/content/translate/`, **preserving this `SOURCE.md`**.
3. Reconcile any entries listed under **Local modifications** below.
4. Update the `Imported on` date above and add a short note describing what changed.

## Local modifications

_(None at import time. Record edits here when they are made: date, reason, files touched.)_
