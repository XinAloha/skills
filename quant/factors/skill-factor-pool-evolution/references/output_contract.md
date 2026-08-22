# Output Contract

运行：

```bash
python scripts/run_factor_pool_evolution.py --input /path/to/evolution_input.json
```

当前脚本是两阶段：

- `prepare`
- `evaluate`

## Prepare 阶段产物

如果还没有用户模型填写好的候选因子，脚本会输出：

```text
<output_dir>/
├── 00_manifest.json
├── input/
│   ├── input_factor_metrics.csv
│   ├── input_factor_daily_metrics.csv
│   ├── input_factor_correlations.csv
│   ├── strong_pool.json
│   └── crossover_pairs.json
└── generation/
    ├── prompts/
    │   ├── mutation_000.prompt.txt
    │   ├── mutation_001.prompt.txt
    │   ├── crossover_000_00.prompt.txt
    │   └── ...
    ├── generated_candidates_template.json
    └── generated_candidates.json
```

### 关键文件

- `input/input_factor_metrics.csv`
  输入因子指标表
- `input/input_factor_correlations.csv`
  输入因子相关性表
- `input/strong_pool.json`
  作为 crossover 主因子来源的 strong pool
- `input/crossover_pairs.json`
  本轮建议的 crossover 配对
- `generation/prompts/`
  提供给当前模型使用的 mutation / crossover prompt pack
- `generation/generated_candidates_template.json`
  用户模型生成候选因子时的模板
- `generation/generated_candidates.json`
  脚本会默认复制一份模板到这里，方便用户直接填写

## Evaluate 阶段产物

当 `generated_candidates.json` 中已经有可用候选后，脚本会继续输出：

```text
<output_dir>/
├── 00_manifest.json
├── input/
├── generation/
│   ├── prompts/
│   ├── generated_candidates_template.json
│   ├── generated_candidates.json
│   ├── mutation_candidates.jsonl
│   ├── mutation_metrics.csv
│   ├── crossover_candidates.jsonl
│   ├── crossover_metrics.csv
│   ├── generated_factor_metrics.csv
│   ├── generated_factor_daily_metrics.csv
│   └── ranked_recommendations.csv
└── final/
    ├── recommended_factors.json
    ├── recommended_factor_values.csv
    ├── next_round_custom_seed_factors.json
    └── recommendation_report.md
```

### 关键文件

- `generation/mutation_candidates.jsonl`
  用户模型生成的 mutation 因子摘要
- `generation/crossover_candidates.jsonl`
  用户模型生成的 crossover 因子摘要
- `generation/generated_factor_metrics.csv`
  所有生成因子的统一指标表
- `generation/ranked_recommendations.csv`
  排名与推荐标注表，至少包含：
  - `rank_ic`
  - `rank_icir`
  - `maxcorr_to_input_pool`
  - `selected_for_recommendation`
  - `maxcorr_to_selected`
  - `recommended_sign`
- `final/recommended_factors.json`
  最终推荐进入下一轮的因子
- `final/recommended_factor_values.csv`
  推荐因子的因子值表
- `final/next_round_custom_seed_factors.json`
  可直接作为下一轮 custom seed 输入的文件
- `final/recommendation_report.md`
  面向人阅读的推荐报告

## `00_manifest.json`

`manifest` 会反映当前阶段：

- `stage = "prepared"`：表示只完成了准备阶段，等待用户模型填写候选文件
- `mode = "evaluated"`：表示已经完成候选评估和推荐输出

## 消费这些结果时的注意点

1. 当前脚本**不内置模型 API 调用**。
2. mutation / crossover 的生成应由当前使用 skill 的模型完成。
3. `generated_candidates.json` 是 prepare 和 evaluate 两阶段之间的桥。
4. `next_round_custom_seed_factors.json` 是最适合直接复用到下一轮输入的文件。
