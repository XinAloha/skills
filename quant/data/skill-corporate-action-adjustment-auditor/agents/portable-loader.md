# Portable Loader Prompt

Use this prompt in agents that do not natively discover `SKILL.md` folders.

```text
You have access to a local skill named corporate-action-adjustment-auditor at:
<CORPORATE_ACTION_ADJUSTMENT_AUDITOR_SKILL_ROOT>

When the user request matches this skill's SKILL.md description:
1. Read <CORPORATE_ACTION_ADJUSTMENT_AUDITOR_SKILL_ROOT>/SKILL.md.
2. Follow the workflow and guardrails in that file exactly.
3. Load referenced files under <CORPORATE_ACTION_ADJUSTMENT_AUDITOR_SKILL_ROOT>/references/ only when needed.
4. Run bundled scripts from the skill root only after reading the relevant instructions.
5. Preserve documented input fields, event conventions, formulas, output contracts, validation limits, and evidence boundaries.
6. Do not invent data interfaces, credentials, corporate actions, or audit results.
```
