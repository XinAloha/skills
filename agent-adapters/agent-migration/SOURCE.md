# Source — `agent-migration`

> Upstream tracking file. Do **not** edit `SKILL.md` here without recording the divergence in **Local modifications** below.

## Upstream

| Field | Value |
|---|---|
| Repository | [dontbesilent2025/dbskill](https://github.com/dontbesilent2025/dbskill) |
| Skill path in repo | `/skills/dbs-agent-migration` |
| Canonical URL | [https://github.com/dontbesilent2025/dbskill/tree/main/skills/dbs-agent-migration](https://github.com/dontbesilent2025/dbskill/tree/main/skills/dbs-agent-migration) |
| Kind | `atomic` |
| Cluster | `-` |
| Imported on | 2026-08-21 |
| License | see upstream `LICENSE` |

**Summary.** Migrate agent workspaces across Claude Code / Codex / Grok.

## Related skills (same cluster)

_(none in cluster)_

## Mounting into another project

This skill folder is self-contained. To use it elsewhere without copying:

```bash
# from the target project root
ln -s /absolute/path/to/skills/agent-adapters/agent-migration/ ./.claude/skills/agent-migration
# or, on Windows (PowerShell, admin):
# New-Item -ItemType Junction -Path .\.claude\skills\agent-migration -Target E:\Project\Quantitative_Trading\skills\agent-adapters/agent-migration
```

If your agent reads from `skill/<name>/SKILL.md`, only the `SKILL.md` is strictly required; `scripts/`, `references/`, and `assets/` are referenced by relative paths inside `SKILL.md`.

## Updating from upstream

1. Pull the latest from `https://github.com/dontbesilent2025/dbskill`.
2. Copy `/skills/dbs-agent-migration` over `skills/agent-adapters/agent-migration/`, **preserving this `SOURCE.md`**.
3. Reconcile any entries listed under **Local modifications** below.
4. Update the `Imported on` date above and add a short note describing what changed.

## Local modifications

_(None at import time. Record edits here when they are made: date, reason, files touched.)_
