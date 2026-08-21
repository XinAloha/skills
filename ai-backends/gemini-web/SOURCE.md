# Source — `gemini-web`

> Upstream tracking file. Do **not** edit `SKILL.md` here without recording the divergence in **Local modifications** below.

> ⚠️ **DANGER**: This skill depends on reverse-engineered / unofficial APIs. Authentication via browser session, cookies, or fragile endpoints. Upstream may break without notice. Use at your own risk.

## Upstream

| Field | Value |
|---|---|
| Repository | [JimLiu/baoyu-skills](https://github.com/JimLiu/baoyu-skills) |
| Skill path in repo | `/skills/baoyu-danger-gemini-web` |
| Canonical URL | [https://github.com/JimLiu/baoyu-skills/tree/main/skills/baoyu-danger-gemini-web](https://github.com/JimLiu/baoyu-skills/tree/main/skills/baoyu-danger-gemini-web) |
| Kind | `composite-danger` |
| Cluster | `-` |
| Imported on | 2026-08-21 |
| License | see upstream `LICENSE` |

**Summary.** DANGER: reverse-engineered Gemini Web API; needs browser session.

## Related skills (same cluster)

_(none in cluster)_

## Mounting into another project

This skill folder is self-contained. To use it elsewhere without copying:

```bash
# from the target project root
ln -s /absolute/path/to/skills/ai-backends/gemini-web/ ./.claude/skills/gemini-web
# or, on Windows (PowerShell, admin):
# New-Item -ItemType Junction -Path .\.claude\skills\gemini-web -Target E:\Project\Quantitative_Trading\skills\ai-backends/gemini-web
```

If your agent reads from `skill/<name>/SKILL.md`, only the `SKILL.md` is strictly required; `scripts/`, `references/`, and `assets/` are referenced by relative paths inside `SKILL.md`.

## Updating from upstream

1. Pull the latest from `https://github.com/JimLiu/baoyu-skills`.
2. Copy `/skills/baoyu-danger-gemini-web` over `skills/ai-backends/gemini-web/`, **preserving this `SOURCE.md`**.
3. Reconcile any entries listed under **Local modifications** below.
4. Update the `Imported on` date above and add a short note describing what changed.

## Local modifications

_(None at import time. Record edits here when they are made: date, reason, files touched.)_
