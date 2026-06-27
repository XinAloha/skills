# Source — `chatroom`

> Upstream tracking file. Do **not** edit `SKILL.md` here without recording the divergence in **Local modifications** below.

## Upstream

| Field | Value |
|---|---|
| Repository | [dontbesilent2025/dbskill](https://github.com/dontbesilent2025/dbskill) |
| Skill path in repo | `/skills/dbs-chatroom` |
| Canonical URL | [https://github.com/dontbesilent2025/dbskill/tree/main/skills/dbs-chatroom](https://github.com/dontbesilent2025/dbskill/tree/main/skills/dbs-chatroom) |
| Kind | `atomic` |
| Cluster | `chatroom` |
| Imported on | 2026-06-27 |
| License | see upstream `LICENSE` |

**Summary.** Multi-expert directed discussion with host and judge.

## Related skills (same cluster)

- [chatroom-austrian](../../methodology/chatroom-austrian/) — Austrian-economics chatroom (Hayek/Mises/Claude roles).

## Mounting into another project

This skill folder is self-contained. To use it elsewhere without copying:

```bash
# from the target project root
ln -s /absolute/path/to/skills/methodology/chatroom/ ./.claude/skills/chatroom
# or, on Windows (PowerShell, admin):
# New-Item -ItemType Junction -Path .\.claude\skills\chatroom -Target E:\Project\Quantitative_Trading\skills\methodology/chatroom
```

If your agent reads from `skill/<name>/SKILL.md`, only the `SKILL.md` is strictly required; `scripts/`, `references/`, and `assets/` are referenced by relative paths inside `SKILL.md`.

## Updating from upstream

1. Pull the latest from `https://github.com/dontbesilent2025/dbskill`.
2. Copy `/skills/dbs-chatroom` over `skills/methodology/chatroom/`, **preserving this `SOURCE.md`**.
3. Reconcile any entries listed under **Local modifications** below.
4. Update the `Imported on` date above and add a short note describing what changed.

## Local modifications

_(None at import time. Record edits here when they are made: date, reason, files touched.)_
