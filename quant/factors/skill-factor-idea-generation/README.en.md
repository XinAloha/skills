# Factor Idea Generation

[简体中文](README.md) | **English**

> When you run out of factor directions, simply ask for a few ideas. The Skill will use its default data scope to generate candidates with economic logic, concrete factor shapes, and explicit risks.

This Community Skill is a **research starting point**. It turns "what else can I investigate?" into implementable and testable factor candidates, but it does not claim that those candidates are empirically effective.

## Quick Start

**Prerequisite: install or enable this Skill in the current agent.** Merely downloading or cloning the GitHub repository does not guarantee that an agent will discover it automatically.

Once enabled, no market-data CSV is required. An agent that supports implicit invocation can trigger the Skill from this request:

```text
I have run out of factor ideas. Please suggest a few.
```

If the platform does not discover it automatically, invoke it explicitly:

```text
Use $factor-idea-generation.
I have run out of factor ideas. Please suggest a few.
```

By default, the Skill uses daily `open/high/low/close/volume`, generates five candidates, and shortlists two for implementation. You may instead provide an OHLCV subset or explicitly add fields such as `amount`, `vwap`, or `turnover`.

You receive:

- A research hypothesis and economic rationale for each candidate.
- A concrete `factor_shape` covering inputs, transformations, window relations, and direction.
- Failure conditions, data risks, and leakage checks.
- A shortlist and, optionally, executable seed code.

## When to Use It

| Your problem | How the Skill helps |
|---|---|
| I have run out of factor ideas | Selects perspectives from the seven-layer research catalog |
| I keep producing momentum or volatility variants | Expands the mechanism space and checks false novelty |
| I have read a useful paper or report | Extracts implementable perspectives as temporary Custom Lenses |
| I want to hand ideas to an evaluation pipeline | Produces structured ideas and optional executable seeds |

The Skill does **not** independently calculate RankIC, RankICIR, backtest returns, or production signals. Those belong to downstream empirical evaluation.

## How It Works

```mermaid
flowchart LR
    A[Make a simple request<br/>optionally add field constraints] --> B[Select research perspectives]
    B --> C[Generate hypotheses and factor shapes]
    C --> D[Check feasibility and duplication]
    D --> E[Return candidates and shortlist]
    E --> F[Optional executable seeds]
```

1. **Understand constraints**: use daily OHLCV by default, or strictly follow a user-provided field scope.
2. **Select perspectives**: choose one or two Lenses from the built-in catalog and optional research context.
3. **Generate candidates**: start with falsifiable hypotheses, then create concrete factor shapes rather than arbitrary operator stacks.
4. **Shortlist**: check leakage, field feasibility, economic logic, and structural duplication.

Each call produces one candidate batch. Feed a shortlist, evaluation feedback, or new research into another call to expand the research space progressively.

## What You Can Provide

| Input | Required | Example |
|---|---|---|
| Available fields | Optional | Defaults to daily `open/high/low/close/volume`; a subset or additional fields may be supplied |
| Market, frequency, and horizon | Optional | A-shares, daily, five-day return |
| Candidate count and preferences | Optional | Defaults to five candidates and a shortlist of two; the user may override either |
| Existing or failed factors | Optional | Used to avoid repeated directions |
| Papers, reports, or notes | Optional | One-run research context |
| Custom Lens Pack | Optional | A reusable user-maintained YAML catalog |

## What the Output Looks Like

```text
Name: Post-compression price-volume release strength
Hypothesis: Synchronized expansion after persistent volume and range compression may indicate a new information-release phase.
Factor shape: compression persistence x continuous price-volume expansion confirmation.
Failure risk: one-day news shocks may create false breakouts.
Status: awaiting implementation and empirical validation.
```

For structured output and handoff formats, see [output_schema.md](references/output_schema.md) and [handoff_schema.md](references/handoff_schema.md).

## Add Your Own Research Perspectives

- **One-run context**: attach a paper, report, or note. The Skill extracts temporary Custom Lenses without modifying the built-in catalog.
- **Reusable extension**: convert useful perspectives into a Custom Lens Pack that can be loaded in future calls.

```text
Use $factor-idea-generation.
Read /path/to/research_report.pdf and extract perspectives implementable with OHLCV.
Combine them with the built-in catalog to generate five candidates and preserve source attribution.
```

See [custom_lens_schema.md](references/custom_lens_schema.md) and [custom_lens_pack.example.yaml](examples/custom_lens_pack.example.yaml).

<details>
<summary><strong>View the built-in seven-layer framework</strong></summary>

The Skill includes 7 Layers, 21 Agents, and 119 Lenses:

1. Market Structure & Cycle
2. Extreme Risk & Fragility
3. Price-Volume Dynamics
4. Price-Volatility Behavior
5. Multi-Scale Complexity
6. Stability & Regime-Gating
7. Geometric & Fusion

Lenses are research perspectives, not validated formulas. See [layer_overview.md](references/layer_overview.md) for the complete catalog.

</details>

## Relationship to Factor Pool Evolution

```text
Factor Idea Generation             Factor Pool Evolution
Propose hypotheses and seeds   ->  Calculate RankIC / RankICIR / maxCorr
Return shortlist or seed code  ->  Evaluate, mutate, and cross over factors
```

## Runtime and Boundaries

- Before use, install/enable the Skill through the platform or place the repository in a Skills directory recognized by the current agent.
- Codex, Claude Code, and OpenClaw: read [SKILL.md](SKILL.md).
- Cursor: use [agents/cursor-rule.mdc](agents/cursor-rule.mdc).
- Hermes and other agents: use [agents/portable-loader.md](agents/portable-loader.md).
- Every candidate is an unvalidated research hypothesis, not investment advice or a promised return.
- This Community Project does not imply official QUANTSKILLS validation, certification, endorsement, or production readiness.

Maintained by Lubin Xie and licensed under [GNU GPL v3.0 only](LICENSE), SPDX `GPL-3.0-only`.
