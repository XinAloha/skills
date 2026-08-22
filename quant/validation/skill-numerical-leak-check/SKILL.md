---
name: numerical-leak-check
description: "当 agent 需要检查时间序列计算、量化因子、特征工程、标签生成、回测信号或研究管线是否存在未来信息泄露时使用。Use this skill for numerical causality checks, lookahead/future-leakage detection, prefix replay, future mutation, batch checking many factors or cases, and writing leak-check reports. This skill is generic: do not assume a fixed factor function shape, schema, asset class, or output column."
license: GPL-3.0-only
metadata:
  quantSkills:
    organization: https://github.com/quantskills
    repository: quantskills/skill-numerical-leak-check
    repository_url: https://github.com/quantskills/skill-numerical-leak-check
    project_type: skill
    collection: factor-research
    license: GPL-3.0-only
    category: factor
    tags: [future-leakage, numerical-causality, factor-research, backtest, lookahead, validation]
    platforms: [claude-code, codex, cursor, hermes, openclaw]
    language: zh-en
    status: draft
    validation_level: listed
    maintainer_type: community
    requires: []
    summary_zh: 用前缀重放和未来扰动对因子、特征、标签或时间序列管线做数值型未来泄露检查。
    summary_en: Run numerical causality checks for factors, features, labels, signals, or time-series pipelines with prefix replay and future mutation.
---

```json qsh-form
{
  "version": 1,
  "task": {
    "placeholder": "请说明或上传待检查的因子、特征、标签、信号或流水线，以及输入输出和生产调用方式",
    "required": true
  },
  "fields": [
    {
      "key": "strictness",
      "label": "检查强度",
      "type": "select",
      "default": "standard",
      "options": [
        { "value": "standard", "label": "标准检查" },
        { "value": "strict", "label": "严格检查（加密切点）" }
      ]
    }
  ],
  "prompt_template": "{{#task}}任务与材料：\n{{task}}\n\n{{/task}}{{#attachments}}用户上传的材料（已放入工作区）：\n{{attachments}}\n\n{{/attachments}}请以 {{strictness}} 强度对待检对象执行通用数值因果性检查，先定义 adapter、输入输出与比较口径，再运行 prefix replay 和 future mutation，覆盖关键窗口及边界切点，汇总 PASS/WARN/FAIL/ERROR、首个失败位置、最大差异、局限与修复建议，输出中文报告。"
}
```

# 数值型未来泄露检查

用这个 skill 检查一个或一批时间序列计算是否把未来信息泄露到历史输出中。默认使用中文进行分析、报告和对话总结。

这个 skill 的核心是传递一种通用检查思想，而不是假定用户的因子接口。不要默认用户代码一定有 `F_*`、`signal`、`period`、OHLCV schema 或特定回测引擎。先理解用户项目，再用 adapter/harness 把项目对象接到数值因果性测试上。

## 核心原则

1. 先定义被检查对象、输入对象、输出对象和比较口径，再运行检查。
2. 至少执行两类测试：prefix replay 和 future mutation。
3. 支持批量检测一批因子、特征、标签、信号或 pipeline case；批量结果必须按 case 汇总。
4. checkpoint 不只用固定比例。围绕 period、window、warmup、resample/session 边界、用户指出的敏感参数和历史失效区间加密。
5. 不把 `PASS` 写成“证明无泄露”。`PASS` 只表示当前数值测试没有发现未来数据影响历史输出。
6. `FAIL` 优先定位首个失败 cut、首个失败位置、测试类型和最大差异，再讨论可能泄露路径。
7. 如果用户项目已有检查器、数据加载器或 pipeline gate，优先复用；否则使用本 skill 的通用 runner 和 adapter 模板。
8. 最终回答不能只给文件路径。必须在对话里暴露状态统计、FAIL/WARN 明细、局限和下一步建议。

## 检查思想

### Prefix replay

先用完整输入计算一次 full output。然后对每个 checkpoint，只保留 checkpoint 及以前的历史输入，重新计算 prefix output。若 full output 在 checkpoint 及以前的历史部分与 prefix output 不一致，说明历史输出依赖了未来输入、全样本状态或非因果缓存。

### Future mutation

先保留 checkpoint 及以前的历史输入不变，把 checkpoint 之后的未来输入替换成极端值、随机值、缺失值或打乱值，再重新计算 mutated output。若 checkpoint 及以前的输出发生变化，说明未来数据影响了历史输出。

## 工作流

### 1. 读取上下文

先识别：

- 用户要检查的是因子、特征、标签、信号、回测 pipeline 还是数据预处理。
- 输入数据的时间轴、实体轴、频率、schema 和真实生产调用方式。
- 输出对象是什么：Series、DataFrame、matrix、dict、文件产物或回测结果。
- 输出比较应该覆盖哪些历史字段、实体、日期和容忍度。
- 是否需要批量检测多个 case，例如多个因子文件、多个参数集、多个数据目录或多个 pipeline 节点。

### 2. 设计 Adapter

不要强行改用户源码。优先写一个临时 adapter/harness，把项目对象接成统一协议。需要详细协议时读取 `references/adapter-contract.md`。

最低协议：

```python
def discover_cases(config):
    ...

def load_input(case, config):
    ...

def run_target(input_obj, case, config):
    ...

def make_prefix(input_obj, cut, case, config):
    ...

def mutate_future(input_obj, cut, case, config):
    ...

def compare_outputs(full_output, test_output, cut, case, config):
    ...
```

如果用户只给一个对象，也仍然可以返回单个 case。批量检测时，`discover_cases()` 返回多个 case；每个 case 应包含稳定的 `case_id` 或可推断名称。

### 3. 选择 Checkpoints

读取 `references/checkpoint-design.md` 后设计切点。默认组合：

- 固定比例：10%、20%、25%、30%、40%、50%、70%、82%、93%。
- 固定位置：20、40、60、80、120、160、200、240、250、252、300、400、500。
- 敏感点邻域：`x-10,x-5,x-3,x-2,x-1,x,x+1,x+2,x+3,x+5,x+10`。
- 随机切点：用于扩大覆盖面。
- 严检模式：围绕可疑区间做连续 cut sweep。

敏感点来自用户参数、period/window/warmup、rolling/min_periods、shift、resample 边界、session 边界、换月/调仓/截面重构日期、历史失败 cut。

### 4. 执行检查

如果已有项目脚本，按项目方式执行，并把结果整理成统一表。

如果需要通用 runner，可使用：

```bash
python <skill_dir>/scripts/run_numerical_leak_check.py \
  --adapter <path/to/leak_check_adapter.py> \
  --config <path/to/config.json> \
  --out-dir <path/to/leak_check_runs/run_name> \
  --workers 1
```

批量检测由 adapter 的 `discover_cases(config)` 决定；runner 会对每个 case 执行 prefix replay 和 future mutation，并输出批量汇总。

初始化 adapter 草稿：

```bash
python <skill_dir>/scripts/init_leak_check_case.py <out_dir>
```

### 5. 解读结果

读取 `references/result-interpretation.md`。统一状态：

- `PASS`：当前测试未发现未来数据影响历史输出。
- `WARN`：有小差异或不稳定现象，需要判断是否为浮点误差、随机性、缓存或弱泄露。
- `FAIL`：未来或全量数据明确改变了历史输出。
- `ERROR`：adapter、目标代码或比较逻辑运行失败。

### 6. 写报告和对话总结

报告参考 `references/report-template.md`。推荐产物：

```text
<out_dir>/
├── leak_check_results.csv
├── leak_check_results.json
├── leak_check_summary.json
└── leak_check_report.md
```

最终对话回答至少包含：

- 检查对象和批量范围。
- adapter/输入/输出/比较口径。
- checkpoint 策略。
- 总体状态统计：case 数、PASS/WARN/FAIL/ERROR 数。
- FAIL/WARN 明细：case、测试类型、cut、最大差异、首个失败位置。
- 对未来泄露风险的解释。
- 本次数值检查的失效条件和未覆盖面。
- 报告与结果文件路径。

不要把完整 CSV 粘贴到对话里；给压缩表和关键证据。
