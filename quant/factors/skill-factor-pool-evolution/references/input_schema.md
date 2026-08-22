# Input Schema

主入口：

```bash
python scripts/run_factor_pool_evolution.py --input /path/to/evolution_input.json
```

如果只是想快速生成一个 demo 输入，先运行：

```bash
python scripts/init_factor_pool.py --output-dir tmp/factor_pool_demo
```

## 核心理念

这个 skill 的脚本**不直接调用模型 API**。  
它分成两个阶段：

1. `prepare`：
   - 评估输入因子
   - 生成 mutation / crossover prompt pack
   - 生成 `generated_candidates_template.json`
2. `evaluate`：
   - 读取由当前模型填写完成的 `generated_candidates.json`
   - 评估这些候选因子
   - 排序并输出推荐结果

## 必填字段

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `market_data_csv_path` | string | 长表 OHLCV CSV 路径，至少包含 `date`, `symbol`, `open`, `high`, `low`, `close`, `volume`。 |
| `seed_alpha_names` | list[string] | 初始 seed 因子名列表。推荐使用 qualified name，例如 `alpha101:alpha_001`。 |

## 常用可选字段

| 字段 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `alpha_library_root` | string | `""` | 外部 `skill-factor-alpha191-alpha101-main` 的根目录。为空时脚本会优先使用 skill 自带的 vendor 目录。 |
| `benchmark_csv_path` | string | `""` | 使用 `alpha191` 且部分公式依赖 benchmark 时提供。 |
| `custom_seed_factors_json_path` | string | `""` | 额外的代码型 seed 因子 JSON。 |
| `output_dir` | string | `outputs/factor_pool_recommendation_demo` | 输出目录。 |
| `mode` | string | `"prepare"` | `prepare`、`evaluate`、`auto` 三选一。`auto` 会在检测到已填写候选文件时自动进入评估阶段。 |
| `generated_candidates_json_path` | string | `""` | 模型生成候选因子的 JSON 路径。为空时默认使用 `<output_dir>/generation/generated_candidates.json`。 |
| `random_seed` | integer | `42` | 仅用于可复现的辅助选择逻辑，不直接驱动模型生成。 |
| `recommendation_top_k` | integer | `0` | 最终推荐多少个因子。`0` 表示等于输入 seed 因子数量。 |
| `recommendation_use_abs_corr` | bool | `true` | 是否按绝对相关性应用推荐去重阈值。 |
| `mutate_strong_pool_only` | bool | `false` | 为 `true` 时只对 strong pool 因子写 mutation 任务；否则对所有输入因子都写 mutation 任务。 |
| `mutation_prompt_note` | string | 见脚本默认值 | 附加到 mutation prompt 的高层指导语。 |
| `crossover_prompt_note` | string | 见脚本默认值 | 附加到 crossover prompt 的高层指导语。 |
| `use_abs_metrics` | bool | `true` | 是否按绝对值使用 `RankIC` / `RankICIR` 做打分。 |
| `target_horizon_days` | integer | `5` | `target_return` 的未来收益 horizon。 |
| `target_price_col` | string | `"open"` | 构造未来收益时使用的价格列。 |
| `min_cross_section_samples` | integer | `3` | 每日横截面评估最少样本数。 |
| `mi_bins` | integer | `10` | 互信息分箱数。 |
| `n_jobs` | integer | `1` | seed library 计算并发度。 |
| `show_progress` | bool | `true` | 是否打印进度日志。 |

## `custom_seed_factors_json_path` 格式

支持两种顶层格式：

1. 直接是数组
2. 对象，且包含 `factors` 字段

每个 factor 至少包含：

```json
{
  "name": "factor_custom_demo",
  "description": "Short explanation",
  "code": "def factor_custom_demo(df): ... return df_copy[factor_name]"
}
```

可选字段：

- `alpha_id`
- `formula`
- `metadata`

这些自定义 seed 因子会通过当前 skill 内置的轻量执行器运行，并和 library factors 一起进入输入因子池。

## 推荐输入示例（prepare 阶段）

```json
{
  "market_data_csv_path": "sample_market_data.csv",
  "alpha_library_root": "",
  "benchmark_csv_path": "",
  "custom_seed_factors_json_path": "",
  "output_dir": "outputs/factor_pool_recommendation_demo",
  "mode": "prepare",
  "generated_candidates_json_path": "",
  "seed_alpha_names": [
    "alpha101:alpha_001",
    "alpha101:alpha_002",
    "alpha101:alpha_003"
  ],
  "random_seed": 42,
  "recommendation_top_k": 0,
  "recommendation_use_abs_corr": true,
  "mutate_strong_pool_only": false,
  "mutation_prompt_note": "Preserve the factor's core economic logic and only improve one or two structural components.",
  "crossover_prompt_note": "Use the stronger factor as the main logic anchor and borrow only complementary low-correlation structure.",
  "use_abs_metrics": true,
  "target_horizon_days": 5,
  "target_price_col": "open",
  "min_cross_section_samples": 3,
  "mi_bins": 10,
  "n_jobs": 1,
  "show_progress": true
}
```

## 模型生成候选文件格式

`generated_candidates.json` 支持两种形态：

1. 顶层对象，包含：
   - `mutation_candidates`
   - `crossover_candidates`
2. 直接是一个平铺数组

每条 candidate 至少包含：

```json
{
  "operator": "mutation",
  "parents": ["alpha101:alpha_001"],
  "name": "factor_new_xxx",
  "description": "What this factor does",
  "formula": "short human-readable formula",
  "code": "def factor_new_xxx(df): ... return df_copy[factor_name]"
}
```

`operator` 可以是：

- `mutation`
- `crossover`

## 典型使用流程

1. 先跑：

```bash
python scripts/run_factor_pool_evolution.py --input /path/to/evolution_input.json
```

如果当前 `generated_candidates_json_path` 里还没有可用候选，脚本会只做 `prepare`，生成：

- `input/`
- `generation/prompts/`
- `generation/generated_candidates_template.json`

2. 让当前使用 skill 的模型读取 prompt pack，并填写 `generated_candidates.json`

3. 再跑一次：

```bash
python scripts/run_factor_pool_evolution.py --input /path/to/evolution_input.json
```

如果检测到可用候选，脚本会进入 `evaluate` 阶段，输出推荐结果。

## 数据列要求

必需列：

```text
date, symbol, open, high, low, close, volume
```

可选列：

```text
amount, vwap, adjfactor, pre_close, limit_up, limit_down
```

如果 `vwap` 缺失而 `amount` 和 `volume` 存在，会自动推导；如果 `amount` 也缺失，底层 library 计算会退化成 `close * volume`。

## 依赖路径解析

当前脚本只要求能访问 `skill-factor-alpha191-alpha101-main`，而且当前 skill 已经自带一份 vendored 运行时。

优先级如下：

1. 输入 JSON 中的 `alpha_library_root`
2. 环境变量 `COGALPHA_FACTOR_POOL_ALPHA_LIBRARY_ROOT`
3. `skill-factor-pool-evolution/vendor/skill-factor-alpha191-alpha101-main`
4. 当前工作区里的 sibling `skill-factor-alpha191-alpha101-main`
