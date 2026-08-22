# Source — `leader`

> Upstream tracking file. Do **not** edit `SKILL.md` here without recording the divergence in **Local modifications** below.

## Upstream

| Field | Value |
|---|---|
| Repository | [KKKKhazix/khazix-skills](https://github.com/KKKKhazix/khazix-skills) |
| Skill path in repo | `/leader` |
| Canonical URL | [https://github.com/KKKKhazix/khazix-skills/tree/main/leader](https://github.com/KKKKhazix/khazix-skills/tree/main/leader) |
| Kind | `composite` |
| Cluster | `-` |
| Imported on | 2026-08-21 |
| License | see upstream `LICENSE` |

**Summary.** Turn a one-line idea into a runnable agent goal brief (<=4000 chars, verified numbers, whitelist bounds, anti-cheat acceptance, resume); splits execution vs exploration.

## Related skills (same cluster)

_(none in cluster)_

## Mounting into another project

This skill folder is self-contained. To use it elsewhere without copying:

```bash
# from the target project root
ln -s /absolute/path/to/skills/workmode/leader/ ./.claude/skills/leader
# or, on Windows (PowerShell, admin):
# New-Item -ItemType Junction -Path .\.claude\skills\leader -Target E:\Project\Quantitative_Trading\skills\workmode/leader
```

If your agent reads from `skill/<name>/SKILL.md`, only the `SKILL.md` is strictly required; `scripts/`, `references/`, and `assets/` are referenced by relative paths inside `SKILL.md`.

## Updating from upstream

1. Pull the latest from `https://github.com/KKKKhazix/khazix-skills`.
2. Copy `/leader` over `skills/workmode/leader/`, **preserving this `SOURCE.md`**.
3. Reconcile any entries listed under **Local modifications** below.
4. Update the `Imported on` date above and add a short note describing what changed.

## Local modifications

_(None at import time. Record edits here when they are made: date, reason, files touched.)_
