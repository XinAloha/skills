---
name: factor-pool-evolution
description: Run one round of factor-pool recommendation from an existing stock alpha set. Use when an agent needs to start from user-provided seed factors, prepare mutation and crossover prompt packs for the current model to reason over, then evaluate generated factors by RankIC and RankICIR and output recommended factors for the next round of iteration, with maxCorr reported as diagnostic context only.
license: GPL-3.0-only
quantSkills:
  organization: https://github.com/quantskills
  repository: quantskills/skill-factor-pool-evolution
  repository_url: https://github.com/quantskills/skill-factor-pool-evolution
  project_type: skill
  collection: factor-evolution
  license: GPL-3.0-only
  category: factor
  tags: [factor-evolution, mutation, crossover, rankic, rankicir]
  platforms: [claude-code, codex, cursor, hermes, openclaw]
  language: zh-en
  status: draft
  validation_level: listed
  maintainer_type: community
  maintainer: Lubin Xie
---

```json qsh-form
{
  "version": 1,
  "task": {
    "placeholder": "请说明本轮因子池演化目标，并提供行情数据、输入 JSON 或 seed 因子材料",
    "required": true
  },
  "fields": [
    {
      "key": "seed_factors",
      "label": "种子因子",
      "type": "textarea",
      "placeholder": "如：alpha101:alpha_001, alpha191:alpha_018；也可通过附件提供"
    },
    {
      "key": "horizon",
      "label": "目标预测周期",
      "type": "select",
      "default": "5",
      "options": [
        { "value": "1", "label": "未来 1 日" },
        { "value": "5", "label": "未来 5 日" },
        { "value": "10", "label": "未来 10 日" },
        { "value": "20", "label": "未来 20 日" }
      ]
    },
    {
      "key": "candidate_count",
      "label": "候选因子数量",
      "type": "number",
      "default": "10",
      "help": "本轮 mutation 与 crossover 合计期望生成的候选数量"
    }
  ],
  "prompt_template": "{{#task}}任务与材料：\n{{task}}\n\n{{/task}}{{#attachments}}用户上传的材料（已放入工作区）：\n{{attachments}}\n\n{{/attachments}}请从现有因子池出发完成一轮 mutation 与 crossover 演化建议。{{#seed_factors}}种子因子为：{{seed_factors}}。{{/seed_factors}}目标预测周期为 {{horizon}} 日，候选因子数量参考 {{candidate_count}}。统一以 RankIC、RankICIR 为主要排序依据，仅将 maxCorr 作为诊断信息，说明输入来源、生成逻辑、评估口径、推荐因子及下一轮用法，并输出中文报告。"
}
```

# Factor Pool Evolution

用这个 skill 做一轮因子池迭代建议。它的目标不是从零挖因子，也不是跑完整论文全流程，而是从一个已有因子池出发，做一轮 `mutation` 和 `crossover` 建议，最后筛出推荐用于下一轮继续迭代的候选因子。

设计灵感来自 CogAlpha 论文里“先理解因子逻辑，再做 mutation / crossover”的思路，但当前 skill 本身是一个更轻量、可复用的一轮工作流。

本项目当前属于 `Community Project`，用于研究与工作流实验，不代表 QUANTSKILLS 官方验证、认证、背书或生产可用结论。

维护者：Lubin Xie。许可证：`GPL-3.0-only`。

## 核心边界

1. 只做一轮因子建议，不做完整多轮 loop。
2. 默认复用内置 vendored 的 `skill-factor-alpha191-alpha101-main` 运行时作为 seed 因子库；也支持通过输入 JSON 或环境变量切换到外部路径。
3. 当前模型负责理解因子逻辑并生成 mutation/crossover 结果；脚本只负责准备提示材料、评估候选因子和整理输出。
4. 主要评估指标为 `RankIC` 和 `RankICIR`；相关性只作为 `maxCorr` 参考输出，不参与推荐过滤。
5. 输出是研究候选因子，不是生产回测结论，也不是交易建议。

## 边界说明

- 数据来源由用户提供，skill 不附带真实市场数据。
- 推荐结果依赖用户输入的行情数据、seed 因子集合、target horizon 与参数配置。
- 结果仅用于研究与教育，不构成投资建议、收益承诺或生产交易信号。
- mutation 和 crossover 生成结果需要进一步样本外验证、风险分析与回测确认。
- 如引用第三方代码、数据、论文或报告，应遵守对应许可证并保留来源说明。

## 何时使用

在这些场景触发：

- 用户已经有一批 seed 因子，想先做一轮建议，再决定下一轮继续怎么迭代。
- 用户想从一批 Alpha101/Alpha191 或自定义因子出发，得到一批推荐的下一轮候选。
- 用户想比较输入因子、mutation 因子、crossover 因子的表现差异，而不是直接跑复杂 loop。

不要在这些场景使用：

- 需要从 OHLCV 零开始提出全新 alpha 想法。
- 需要完整的 CogAlpha 多 agent 生成、quality checker、adaptive feedback、fresh alpha injection。
- 需要 portfolio backtest、成本分析、换手分析或因子推广决策。

## 工作流

### 1. 准备输入

先读取 `references/input_schema.md`。

输入至少需要：

- `market_data_csv_path`
- `seed_alpha_names`
- 可选的 `custom_seed_factors_json_path`

如果需要快速创建一个 demo 输入，运行：

```bash
python scripts/init_factor_pool.py --output-dir tmp/factor_pool_demo
```

它会生成：

- 示例行情 CSV
- 示例 `evolution_input.json`
- 可选的 `custom_seed_factors_template.json`

### 2. 计算 seed 因子

优先从 `skill-factor-alpha191-alpha101-main` 计算 seed 因子值，也支持用户自定义代码型 seed 因子。

依赖路径解析顺序：

1. 输入 JSON 中的 `alpha_library_root`
2. 环境变量 `COGALPHA_FACTOR_POOL_ALPHA_LIBRARY_ROOT`
3. skill 自带的 `vendor/skill-factor-alpha191-alpha101-main`
4. 当前工作区里的 sibling fallback

当前实现支持：

- `alpha101:alpha_001` 这类 qualified seed name
- `alpha191:alpha_018` 这类 qualified seed name
- 可选的 `custom_seed_factors_json_path`，用于补充用户自己的代码型 seed 因子

如果用了 `alpha191` 因子且公式依赖 benchmark，按输入文件提供 `benchmark_csv_path`。

### 3. 评估 seed pool

对所有 seed 因子统一计算：

- `IC`
- `RankIC`
- `ICIR`
- `RankICIR`
- `MI`

然后按 `RankICIR` 主排序、`RankIC` 次排序，选出表现更强的因子；当前实现会取前 50% 作为 `strong pool`，并为后续 `crossover` 预先挑选低相关的配对对象。

### 4. 运行一轮建议生成

这一轮会做两类生成：

- `mutation`
- `crossover`

默认规则：

1. 脚本先对所有输入因子做评估，并写出 strong pool / crossover pairs / prompt pack。
2. 当前模型读取这些 prompt，生成 mutation / crossover 候选，并填回 `generated_candidates.json`。
3. 脚本再次运行，对这些候选统一评估。
4. 先按 `RankIC`、`RankICIR` 排序。
5. 输出 `maxCorr` 作为相关性参考。
6. 输出推荐用于下一轮继续迭代的因子。

当前 skill 不在脚本内部调用模型 API；mutation / crossover 应由**当前正在使用这个 skill 的模型**完成。详细规则见 `references/evolution_rules.md`。

### 5. 读取结果并回答用户

运行完成后先读取 `references/output_contract.md`，再消费产物。

最终对话回复不能只说“结果在某个文件里”。至少要包含：

- 本轮输入因子来源和数量
- 评价口径：数据、target horizon、排序指标
- mutation 生成了哪些因子
- crossover 生成了哪些因子
- 最终推荐因子的指标、相关性和推荐方向
- 下一步如何把推荐因子作为下一轮输入继续运行

## 资源

### scripts/

- `scripts/init_factor_pool.py`
  用于初始化 demo 数据和输入 JSON。
- `scripts/run_factor_pool_evolution.py`
  主执行入口。负责输入因子评估、prompt pack 准备、候选因子评估、排序和产物落盘。

### references/

- `references/input_schema.md`
  输入 JSON 字段说明。
- `references/output_contract.md`
  一轮推荐版的输出目录和关键文件说明。
- `references/evolution_rules.md`
  当前一轮 mutation/crossover 规则与模型生成约束。

## 实现说明

这个 skill 当前是“最小可跑版”：

- 复用了 Alpha101/Alpha191 因子计算能力；
- 本地内置了 `target_return` 与 `RankIC/RankICIR` 评估逻辑；
- 没有直接复用完整 CogAlpha graph；
- 真正的 mutation / crossover 推理由当前模型完成，脚本只负责准备与评估。

如果用户想继续迭代，直接把本轮输出的推荐因子作为下一轮输入再次运行即可。
