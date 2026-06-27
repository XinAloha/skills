# Source — `image-gen`

> Upstream tracking file. Do **not** edit `SKILL.md` here without recording the divergence in **Local modifications** below.

## Upstream

| Field | Value |
|---|---|
| Repository | [JimLiu/baoyu-skills](https://github.com/JimLiu/baoyu-skills) |
| Skill path in repo | `/skills/baoyu-image-gen` |
| Canonical URL | [https://github.com/JimLiu/baoyu-skills/tree/main/skills/baoyu-image-gen](https://github.com/JimLiu/baoyu-skills/tree/main/skills/baoyu-image-gen) |
| Kind | `composite` |
| Cluster | `-` |
| Imported on | 2026-06-27 |
| License | see upstream `LICENSE` |

**Summary.** Multi-provider image generation API (OpenAI/Azure/Google/OpenRouter/DashScope/Z.AI/MiniMax/Jimeng/Seedream/Replicate/Agnes).

## Related skills (same cluster)

_(none in cluster)_

## Mounting into another project

This skill folder is self-contained. To use it elsewhere without copying:

```bash
# from the target project root
ln -s /absolute/path/to/skills/ai-backends/image-gen/ ./.claude/skills/image-gen
# or, on Windows (PowerShell, admin):
# New-Item -ItemType Junction -Path .\.claude\skills\image-gen -Target E:\Project\Quantitative_Trading\skills\ai-backends/image-gen
```

If your agent reads from `skill/<name>/SKILL.md`, only the `SKILL.md` is strictly required; `scripts/`, `references/`, and `assets/` are referenced by relative paths inside `SKILL.md`.

## Updating from upstream

1. Pull the latest from `https://github.com/JimLiu/baoyu-skills`.
2. Copy `/skills/baoyu-image-gen` over `skills/ai-backends/image-gen/`, **preserving this `SOURCE.md`**.
3. Reconcile any entries listed under **Local modifications** below.
4. Update the `Imported on` date above and add a short note describing what changed.

## Local modifications

_(None at import time. Record edits here when they are made: date, reason, files touched.)_
