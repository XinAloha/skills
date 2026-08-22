# Portable Loader Prompt

Use this prompt in agents that do not natively discover `SKILL.md` folders.

```text
You have access to a local skill named index-rebalance-event-study at:
<INDEX_REBALANCE_EVENT_STUDY_SKILL_ROOT>

When the user request matches this skill's SKILL.md description:
1. Read <INDEX_REBALANCE_EVENT_STUDY_SKILL_ROOT>/SKILL.md.
2. Follow the workflow and guardrails in that file exactly.
3. Load referenced files under <INDEX_REBALANCE_EVENT_STUDY_SKILL_ROOT>/references/ only when needed.
4. Run bundled scripts from the skill root only after reading the relevant instructions.
5. Preserve documented event anchors, input fields, formulas, output contracts, validation limits, and evidence boundaries.
6. Do not invent data interfaces, credentials, index notices, events, or study results.
```
