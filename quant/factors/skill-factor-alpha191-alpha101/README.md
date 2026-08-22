# skill-factor-alpha191-alpha101

**简体中文** | [English](README.en.md)

> 参考自 JoinQuant 公式的 Alpha101 + Alpha191 因子库：从长表 OHLCV CSV 批量计算每日因子值，输出宽表因子 CSV。

<p align="center">
  <img alt="libraries" src="https://img.shields.io/badge/libraries-Alpha101%20%2B%20Alpha191-blue">
  <img alt="factors" src="https://img.shields.io/badge/factors-292-brightgreen">
  <img alt="type" src="https://img.shields.io/badge/type-factor--library-blue">
  <img alt="platform" src="https://img.shields.io/badge/platform-Codex-9cf">
  <img alt="status" src="https://img.shields.io/badge/status-stable-brightgreen">
  <img alt="validation" src="https://img.shields.io/badge/validation-L3%20verified-success">
  <img alt="license" src="https://img.shields.io/badge/license-GPLv3-blue">
</p>

`skill-factor-alpha191-alpha101` 是一个经典公式因子库 Skill，用于计算参考自 JoinQuant 公式的 Alpha101 和 Alpha191 因子值。

这个仓库适合用于研究：

- Alpha101 / Alpha191 经典公式因子的批量生成
- A 股日频 OHLCV 长表数据的因子矩阵构建
- 后续因子评价、因子筛选、模型训练或回测前的数据准备
- Codex 对话中触发确定性因子计算工作流

本仓库只负责计算因子值，不调用 LLM，不读取 API key，也不输出 IC、ICIR、回测收益或交易建议。

## 仓库内容

本仓库包含两套公式因子库：

| 因子库 | 范围 | 输出文件 | 说明 |
|---|---:|---|---|
| Alpha101 | `alpha_001` 到 `alpha_101` | `alpha101_values.csv` | 参考 JoinQuant Alpha101 的公式 |
| Alpha191 | `alpha_001` 到 `alpha_191` | `alpha191_values.csv` | 参考 JoinQuant Alpha191 的公式 |

公式实现从本地 `compute_alpha101_skill.py` 和 `compute_alpha191_skill.py` 迁移为可通过 CLI 和 Codex 调用的自包含结构。Alpha101 和 Alpha191 均参考 JoinQuant 公式实现，并根据 JoinQuant 提供的因子值 API 做过修正。

部分公式依赖行业、市值、基准指数或其他输入。当前数据不足时，相关因子不会终止整个任务，而是记录到 `skipped_factors.json`。

## 目录结构

```text
skill-factor-alpha191-alpha101/
├── SKILL.md
├── README.md
├── README.en.md
├── agents/
│   └── openai.yaml
├── examples/
│   ├── compute_input.json
│   └── toy_market_data.csv
├── references/
│   ├── input_schema.md
│   ├── output_contract.md
│   ├── source_boundary.md
│   └── validation_notes.md
└── scripts/
    ├── compute_alpha_factors.py
    └── alpha_runtime/
        ├── alpha101_formulas.py
        ├── alpha191_formulas.py
        ├── alpha_compute.py
        ├── data.py
        ├── runtime.py
        └── selector.py
```

## 数据要求

第一版只支持长表 CSV。每一行是一只股票在一个交易日的行情记录。

必需字段：

```text
date, symbol, open, high, low, close, volume
```

可选字段：

```text
amount, vwap, adjfactor, pre_close, limit_up, limit_down
```

处理规则：

| 字段/规则 | 说明 |
|---|---|
| `date` | 支持 `YYYYMMDD` 或 `YYYY-MM-DD`，运行时会标准化为 `YYYYMMDD` |
| `symbol` | 按字符串处理 |
| `vwap` 缺失 | 若有 `amount` 和 `volume`，用 `amount / volume` 推导 |
| `amount` 缺失 | 用 `close * volume` 近似 |
| `adjfactor` 存在 | 价格字段会转换为未复权口径后再计算 |
| `benchmark_csv_path` | 可选；用于 Alpha191 中需要基准指数的公式 |

## 快速开始

安装依赖：

```bash
pip install -r requirements.txt
```

运行示例配置：

```bash
python scripts/compute_alpha_factors.py --input examples/compute_input.json
```

指定输出目录：

```bash
python scripts/compute_alpha_factors.py --input examples/compute_input.json --output outputs/my_alpha_run
```

`--output` 会覆盖 JSON 中的 `output_dir`。

## 输入配置

示例见 [examples/compute_input.json](examples/compute_input.json)。

```json
{
  "market_data_csv_path": "toy_market_data.csv",
  "output_dir": "outputs/alpha_compute_example",
  "alpha_sets": ["alpha101", "alpha191"],
  "alpha_names": [
    "alpha101:alpha_001",
    "alpha101:alpha_002",
    "alpha191:alpha_001",
    "alpha191:alpha_018"
  ],
  "exclude_alpha_names": [],
  "start_date": "",
  "end_date": "",
  "symbols": [],
  "output_format": "csv",
  "output_layout": "wide",
  "n_jobs": 1,
  "show_progress": true
}
```

核心字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `market_data_csv_path` | string | 长表行情 CSV 路径。相对路径依次按输入 JSON 目录、Skill 根目录、`examples/` 解析 |
| `benchmark_csv_path` | string | 可选基准指数 CSV，字段至少包含 `date`，并包含 `close` 或 `open` |
| `output_dir` | string | 输出目录。JSON 内相对路径按 Skill 根目录解析 |
| `alpha_sets` | list/string | 可选 `alpha101`、`alpha191` 或两者；为空表示两者都计算 |
| `alpha_names` | list/string | 为空表示计算所选库全部因子；支持 `alpha_001`、`1`、`alpha101:alpha_001` |
| `exclude_alpha_names` | list/string | 在选择后排除指定因子，支持带库名前缀 |
| `start_date` / `end_date` | string | 可选日期过滤，闭区间 |
| `symbols` | list[string] | 可选股票池过滤，空列表表示全部股票 |
| `n_jobs` | integer | 并行 worker 数；缺省时使用机器逻辑 CPU 数 |
| `show_progress` | bool | 是否打印进度条 |

`output_format` 和 `output_layout` 当前只作为示例说明字段保留。实际代码固定输出 CSV 宽表；修改这两个字段不会改变输出格式。

## 因子选择方式

只计算 Alpha101：

```json
{
  "alpha_sets": ["alpha101"],
  "alpha_names": []
}
```

只计算 Alpha191：

```json
{
  "alpha_sets": ["alpha191"],
  "alpha_names": []
}
```

同时计算两套库的指定因子：

```json
{
  "alpha_sets": ["alpha101", "alpha191"],
  "alpha_names": ["alpha101:alpha_001", "alpha191:alpha_018"]
}
```

排除指定因子：

```json
{
  "alpha_sets": ["alpha191"],
  "exclude_alpha_names": ["alpha_075", "alpha_181"]
}
```

## 输出文件

运行结果写入 `output_dir`：

```text
outputs/alpha_compute_example/
├── alpha101_values.csv
├── alpha191_values.csv
├── alpha_compute_summary.json
├── skipped_factors.json
└── run_config.json
```

| 文件 | 内容 |
|---|---|
| `alpha101_values.csv` | Alpha101 宽表因子值；仅当至少一个 Alpha101 因子成功计算时生成 |
| `alpha191_values.csv` | Alpha191 宽表因子值；仅当至少一个 Alpha191 因子成功计算时生成 |
| `alpha_compute_summary.json` | 本次运行的输入路径、输出路径、样本区间、因子数量、跳过数量等摘要 |
| `skipped_factors.json` | 返回 `None` 或计算失败的因子列表 |
| `run_config.json` | 本次运行使用的输入配置副本 |

宽表 CSV 格式：

```text
date,symbol,alpha_001,alpha_002,...
```

每一行对应一个 `(date, symbol)`，每个因子是一列。Alpha101 和 Alpha191 分别输出为独立文件，不混在同一个 CSV 里。

## 运行大样本时的建议

全市场、长时间区间、全 Alpha101/Alpha191 会生成很大的宽表 CSV。建议：

- Alpha101 和 Alpha191 分开运行，降低内存和 IO 峰值。
- `n_jobs` 不要盲目设置为机器最大核数；并行越高，内存、进程调度和写盘压力越大。
- 如果服务器已有其他计算任务，先用 `n_jobs: 8`、`16` 或 `24` 试跑。
- 真实生产验证前，先用较短日期区间和少量因子做 smoke test。

## 验证口径

当前验证等级是 `L3 verified`。这里的 verified 指公式库复现、真实数据运行完整性和 Codex 运行一致性验证，不代表预测收益或交易收益验证。

已验证内容：

- 真实 A 股长表 OHLCV 数据运行通过，样本区间为 `20230601` 到 `20251231`。
- Alpha101 请求 101 个因子，成功计算 82 个，部分依赖外部数据源暂未验证。
- Alpha191 请求 191 个因子，成功计算 186 个，部分依赖外部数据源暂未验证。
- Codex Skill 输出与开发目录输出在行数、列、`date` / `symbol` key 和 NaN 位置上保持一致。
- 指定因子计算结果与全量计算中对应列完全一致。

未声明内容：

- 不声明 IC、ICIR 或多空收益有效。
- 不声明交易收益或投资可用性。
- 不单独提供回测结果。

## 项目状态与风险边界

- **项目状态**：Community Project，未经 QUANTSKILLS 官方审核、认证或背书。
- **数据来源**：本仓库只包含 toy data；真实行情、基准、行业、市值或其他数据由使用者自行提供，并由使用者负责数据许可与合规。
- **公式来源**：Alpha101 和 Alpha191 参考 JoinQuant 公式实现，并根据用户授权的 JoinQuant 因子值 API 对比结果做过修正。
- **核心假设**：输入为日频长表 OHLCV CSV；字段定义、复权口径、股票池、交易日历和缺失值处理会影响最终因子值。
- **已知限制**：部分因子依赖行业、市值、基准指数或其他外部字段；当输入字段不足时会进入 `skipped_factors.json`。
- **风险边界**：输出仅为公式因子值，不代表因子有效性、预测能力、交易信号、组合收益或生产可用性。
- **用途**：仅供量化研究、教育和方法论参考，不构成投资建议、调仓建议或收益承诺。

## 边界

| 边界 | 说明 |
|---|---|
| Factor Library | 只计算 Alpha101/Alpha191 因子值 |
| 无 LLM 依赖 | 不调用模型，不读取 API key |
| 无因子评价 | 不计算 IC、ICIR、Rank IC、分组收益或回测收益 |
| 无交易建议 | 不输出投资建议、调仓建议或收益承诺 |
| 长表 CSV 输入 | 第一版不支持数据库、parquet、实时 API 或分钟级输入 |
| 宽表 CSV 输出 | 当前固定输出宽表 CSV |

## License

This repository is licensed under the GNU General Public License v3.0. See [LICENSE](LICENSE).
