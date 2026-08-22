---
name: factor-ranking-sage
description: "Rank and select quantitative model factors from local factor and label CSV files with regression mRMR using F-statistic relevance and Pearson redundancy, or fixed-model Marginal-SAGE MSE contribution for LGBM and MLP. Use when an agent needs reproducible Top-K factor rankings, mRMR redundancy filtering, SAGE global contribution estimates, convergence diagnostics, or auditable selection artifacts."
metadata:
  short-description: Regression mRMR or fixed-model Marginal-SAGE factor ranking
  quantSkills:
    organization: QuantSkills
    organization_url: https://github.com/quantskills
    repository: skill-factor-ranking-sage
    repository_url: https://github.com/quantskills/skill-factor-ranking-sage
    project_type: skill
    collection: factor-selection
    license: GPL-3.0-only
    category: tooling
    tags: [factor-selection, mrmr, sage, model-interpretability]
    platforms: [codex]
    language: zh-en
    status: active
    validation_level: runnable
    maintainer_type: community
    requires: []
    summary_zh: 使用回归 mRMR 或固定模型 Marginal-SAGE 对量化多因子数据进行可复现 Top-K 排名。
    summary_en: Rank quantitative model factors with local regression mRMR or fixed-model Marginal-SAGE and export reproducible Top-K artifacts.
---

# Factor Ranking SAGE

Use this skill to rank local quantitative factors with one supported method per run.

## Core Workflow

1. Read references/input_schema.md before preparing the input JSON.
2. Provide local factor and label CSV files with one unique row per (date, ticker) observation.
3. Configure one fixed train/validation split and an embargo suitable for the label horizon.
4. Choose one mode:
   - Use mode=mrmr for deterministic regression F-statistic relevance and Pearson-redundancy Top-K selection on training rows.
   - Use mode=sage for fixed-model Marginal-SAGE MSE contribution. Choose model.type=lgbm or model.type=mlp.
5. Run the matching smoke configuration first:

~~~bash
python scripts/run_factor_selection.py --input examples/factor_selection_mrmr_smoke.json
python scripts/run_factor_selection.py --input examples/factor_selection_lgbm_smoke.json
python scripts/run_factor_selection.py --input examples/factor_selection_mlp_smoke.json
~~~

6. Run the user's JSON through the same CLI:

~~~bash
python scripts/run_factor_selection.py --input <input-json>
~~~

7. Read references/output_contract.md before consuming selected_factors.json, the method-specific ranking CSV, and selection_report.md.
8. Keep a locked holdout outside the selection run and independently compare the selected subset with full-factor and random-subset baselines.

## Method Boundaries

- Run mRMR and SAGE independently. Do not combine their scores.
- In mRMR mode, use training rows only. The validation rows are retained for split consistency but are not used by the selector.
- In SAGE mode, fit one configured model on training rows and explain sampled validation loss with the local empirical MarginalImputer and permutation estimator.
- Treat SAGE convergence metadata and standard errors as required diagnostics, not optional details.
- Treat each Top-K result as the ordered output of the configured ranking method, with K supplied by the user.
- Keep the runtime limited to the two documented ranking modes and their output contracts.

## Output Contract

Write each run under output_root/runs/<run_id>/ with common manifests, a selected-factor JSON, a report, and mode-specific artifacts:

- mRMR: mrmr_ranking.csv and mrmr_redundancy_matrix.csv
- SAGE: sage_values.csv and sage_metadata.json

## References

- Use references/source_boundary.md for data, algorithm, and research boundaries.
- Use references/input_schema.md for input fields and mode-specific configuration.
- Use references/output_contract.md for artifact names and result fields.
- Use references/metric_definitions.md to interpret mRMR and SAGE values.
- Use references/validation_notes.md before assigning research meaning to a ranking.
- Use references/algorithm_sources.md for algorithm provenance and license notices.
