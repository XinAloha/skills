# Portable Loader

Use this loader with Hermes or OpenClaw when the runtime does not natively
discover `SKILL.md` folders. If native skill discovery is available, install
the full folder unchanged and load `SKILL.md` directly.

```text
You have access to a local skill named portfolio-attribution at:
<PORTFOLIO_ATTRIBUTION_SKILL_ROOT>

When the user asks for portfolio attribution, performance attribution, active
return sources, Brinson-Fachler analysis, or factor contributions:
1. Read <PORTFOLIO_ATTRIBUTION_SKILL_ROOT>/SKILL.md.
2. Read <PORTFOLIO_ATTRIBUTION_SKILL_ROOT>/references/methodology.md before
   interpreting formulas or changing attribution assumptions.
3. Validate weights, returns, sectors, duplicate keys, and data coverage.
4. Use scripts/attribution.py for deterministic calculations.
5. Preserve all identity assertions; refuse to publish a report that does not
   reconcile to interval active return.
6. Report data sources, benchmark, period, assumptions, limitations, and risk
   boundaries. Do not provide trading instructions or performance promises.
```

Runtime placement:

- Codex: install under a Codex skill path and invoke `$portfolio-attribution`.
- Claude Code: install under a Claude skill path and invoke
  `$portfolio-attribution`.
- Cursor: copy to `.cursor/skills/portfolio-attribution` and enable
  `agents/cursor-rule.mdc`.
- Hermes/OpenClaw: mount the folder as a local skill root or paste the loader
  above with the real path.
