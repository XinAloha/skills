# Portable Runtime Loader

This skill uses `SKILL.md` as its canonical instruction set. A runtime adapter should load that file and resolve paths relative to the repository root.

## Runtime mapping

- **Codex:** install under `.agents/skills/statistical-arbitrage-time-series` or `~/.agents/skills/...`; load `SKILL.md`.
- **Claude Code:** install under `.claude/skills/statistical-arbitrage-time-series` or `~/.claude/skills/...`; load `SKILL.md`.
- **Cursor:** use [`cursor-rule.mdc`](cursor-rule.mdc) and load `SKILL.md` for the active workspace.
- **Hermes:** load this file, then `SKILL.md`.
- **OpenClaw:** load [`openai.yaml`](openai.yaml), then `SKILL.md`.

The bundled script is optional tooling; it must not be treated as financial advice or as a guarantee of research validity.
