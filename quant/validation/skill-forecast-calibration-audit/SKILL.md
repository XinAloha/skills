---
name: skill-forecast-calibration-audit
description: Audit binary probability forecasts with reliability bins, Brier score, log loss, calibration intercept and slope, threshold metrics, and time-sliced diagnostics. Use when an agent needs to evaluate whether model probabilities are trustworthy for research or decision thresholds.
quantSkills:
  organization: https://github.com/quantskills
  repository: quantskills/skill-forecast-calibration-audit
  repository_url: https://github.com/quantskills/skill-forecast-calibration-audit
  project_type: skill
  collection: forecast-analysis
  license: GPL-3.0-only
  category: trader-research
  tags: [forecast, calibration, reliability, probability]
  platforms: [claude-code, codex, cursor, hermes, openclaw]
  language: zh-en
  status: stable
  validation_level: runnable
  maintainer_type: community
  requires: []
  summary_zh: 审计二元概率预测的可靠性、评分、阈值表现和按时间切片的漂移。
  summary_en: Audit binary forecast reliability, proper scores, thresholds, and chronological drift diagnostics.
---

<!-- qsh-form is optional; this declaration enables a structured run form in quantskillhub. -->
```json qsh-form
{
  "version": 1,
  "task": {
    "placeholder": "例如：审计这批概率预测是否过度自信并检查时间漂移",
    "required": true
  },
  "fields": [
    {"key": "forecasts_csv", "type": "text", "label": "预测 CSV"},
    {"key": "threshold", "type": "number", "label": "分类阈值"},
    {"key": "time_bins", "type": "number", "label": "时间分箱数"},
    {"key": "regime_column", "type": "text", "label": "分组列（可选）"}
  ],
  "prompt_template": "请处理任务：{{task}}；预测文件：{{forecasts_csv}}；阈值：{{threshold}}；时间分箱：{{time_bins}}；分组列：{{regime_column}}。附件：{{#attachments}}"
}
```

# Forecast Calibration Audit

Use this skill to distinguish a forecast that ranks well from one whose probabilities are numerically credible. It produces reliability tables, proper scoring rules, threshold metrics, and chronological diagnostics while preserving the original observations.

## Core Workflow

1. Read [references/input_contract.md](references/input_contract.md). Confirm every probability is in `[0, 1]` and every outcome is a realized 0/1 label.
2. Sort by the supplied date and choose chronological bins before reviewing aggregate results. Never randomly shuffle a time series.
3. Run `scripts/calibrate_forecasts.py` to calculate Brier score, clipped log loss, ECE/MCE, calibration intercept/slope, and threshold metrics.
4. Inspect `reliability.csv` for systematic over- or under-confidence and `time_metrics.csv` for drift.
5. Treat small bins as indicative only; report count, date range, and class balance. When changing probabilities, calibrate on an earlier window and validate on a later window.

## Command

```bash
python scripts/calibrate_forecasts.py --input forecasts.csv --output-dir calibration_out \
  --threshold 0.5 --time-bins 5
```

Use `--demo --output-dir calibration_out` for a deterministic smoke test.

## Output Contract

- `scored_predictions.csv`: original rows plus predicted class and per-row Brier/log-loss terms.
- `reliability.csv`: fixed probability bins with count, mean forecast, observed rate, gap, and weighted gap.
- `time_metrics.csv`: metrics for chronological time slices.
- `summary.json`: aggregate metrics, calibration coefficients, class balance, and warnings.

Use calibration slope/intercept as diagnostics, not as a substitute for a held-out recalibration model. A perfect score on a tiny sample is not evidence of generalization.

## Boundaries

- Use this skill for probabilistic or directional forecast quality.
- Do not use it as a replacement for factor evaluation, IC analysis, or earnings tracking.
- Do not turn calibration metrics into investment advice or claim causal validity.
- Follow [references/source_boundary.md](references/source_boundary.md) for permitted sources.
