# Source — `wechat-summary`

> Upstream tracking file. Do **not** edit `SKILL.md` here without recording the divergence in **Local modifications** below.

## Upstream

| Field | Value |
|---|---|
| Repository | [JimLiu/baoyu-skills](https://github.com/JimLiu/baoyu-skills) |
| Skill path in repo | `/skills/baoyu-wechat-summary` |
| Canonical URL | [https://github.com/JimLiu/baoyu-skills/tree/main/skills/baoyu-wechat-summary](https://github.com/JimLiu/baoyu-skills/tree/main/skills/baoyu-wechat-summary) |
| Kind | `composite` |
| Cluster | `-` |
| Imported on | 2026-06-27 |
| License | see upstream `LICENSE` |

**Summary.** Summarize WeChat group chats via local wx-cli (macOS).

## Related skills (same cluster)

_(none in cluster)_

## Mounting into another project

This skill folder is self-contained. To use it elsewhere without copying:

```bash
# from the target project root
ln -s /absolute/path/to/skills/productivity/wechat-summary/ ./.claude/skills/wechat-summary
# or, on Windows (PowerShell, admin):
# New-Item -ItemType Junction -Path .\.claude\skills\wechat-summary -Target E:\Project\Quantitative_Trading\skills\productivity/wechat-summary
```

If your agent reads from `skill/<name>/SKILL.md`, only the `SKILL.md` is strictly required; `scripts/`, `references/`, and `assets/` are referenced by relative paths inside `SKILL.md`.

## Updating from upstream

1. Pull the latest from `https://github.com/JimLiu/baoyu-skills`.
2. Copy `/skills/baoyu-wechat-summary` over `skills/productivity/wechat-summary/`, **preserving this `SOURCE.md`**.
3. Reconcile any entries listed under **Local modifications** below.
4. Update the `Imported on` date above and add a short note describing what changed.

## Local modifications

_(None at import time. Record edits here when they are made: date, reason, files touched.)_
