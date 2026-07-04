# Source — `ponytail-debt`

> Upstream tracking file. Do **not** edit `SKILL.md` here without recording the divergence in **Local modifications** below.

## Upstream

| Field | Value |
|---|---|
| Repository | [DietrichGebert/ponytail](https://github.com/DietrichGebert/ponytail) |
| Skill path in repo | `/skills/ponytail-debt` |
| Canonical URL | [https://github.com/DietrichGebert/ponytail/tree/main/skills/ponytail-debt](https://github.com/DietrichGebert/ponytail/tree/main/skills/ponytail-debt) |
| Kind | `atomic` |
| Cluster | `ponytail` |
| Imported on | 2026-07-04 |
| License | see upstream `LICENSE` |

**Summary.** Harvest every ponytail: comment into a debt ledger so deliberate shortcuts get tracked. One-shot report, changes nothing.

## Related skills (same cluster)

- [ponytail](../../workmode/ponytail/) — Lazy senior-dev coding mode: force the minimal solution that works (YAGNI -> stdlib -> native -> one line -> minimum).
- [ponytail-review](../../workmode/ponytail-review/) — Code review hunting only over-engineering: one line per finding (delete/stdlib/native/yagni/shrink).
- [ponytail-audit](../../workmode/ponytail-audit/) — Whole-repo audit for over-engineering: ranked list of what to delete/simplify/replace with stdlib/native.
- [ponytail-gain](../../workmode/ponytail-gain/) — Display ponytail's measured benchmark scoreboard (less code/cost, more speed).
- [ponytail-help](../../workmode/ponytail-help/) — Quick-reference card for all ponytail modes/skills/commands.

## Mounting into another project

This skill folder is self-contained. To use it elsewhere without copying:

```bash
# from the target project root
ln -s /absolute/path/to/skills/workmode/ponytail-debt/ ./.claude/skills/ponytail-debt
# or, on Windows (PowerShell, admin):
# New-Item -ItemType Junction -Path .\.claude\skills\ponytail-debt -Target E:\Project\Quantitative_Trading\skills\workmode/ponytail-debt
```

If your agent reads from `skill/<name>/SKILL.md`, only the `SKILL.md` is strictly required; `scripts/`, `references/`, and `assets/` are referenced by relative paths inside `SKILL.md`.

## Updating from upstream

1. Pull the latest from `https://github.com/DietrichGebert/ponytail`.
2. Copy `/skills/ponytail-debt` over `skills/workmode/ponytail-debt/`, **preserving this `SOURCE.md`**.
3. Reconcile any entries listed under **Local modifications** below.
4. Update the `Imported on` date above and add a short note describing what changed.

## Local modifications

_(None at import time. Record edits here when they are made: date, reason, files touched.)_
