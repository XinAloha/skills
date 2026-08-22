# Portable Loader Prompt

Use this prompt in agents that do not natively discover `SKILL.md` folders.

```text
You have access to a local skill named portfolio-liquidity-stress-test at:
<PORTFOLIO_LIQUIDITY_STRESS_TEST_SKILL_ROOT>

When the user request matches this skill's SKILL.md description:
1. Read <PORTFOLIO_LIQUIDITY_STRESS_TEST_SKILL_ROOT>/SKILL.md.
2. Follow the workflow and guardrails in that file exactly.
3. Load referenced files under <PORTFOLIO_LIQUIDITY_STRESS_TEST_SKILL_ROOT>/references/ only when needed.
4. Run bundled scripts from the skill root only after reading the relevant instructions.
5. Preserve documented input fields, liquidation assumptions, formulas, output contracts, validation limits, and risk boundaries.
6. Do not invent holdings, data interfaces, credentials, market inputs, or stress-test results.
```
