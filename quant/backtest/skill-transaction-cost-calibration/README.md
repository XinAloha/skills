<div align="center">
  <h1>交易成本校准</h1>
  <p>从成交与成交前市场数据中，校准可解释的执行摩擦模型。</p>
  <p>
    <a href="README.en.md">English</a>
    ·
    <a href="https://github.com/quantskills/skill-transaction-cost-calibration/issues">反馈问题</a>
  </p>
  <p>
    <img src="https://img.shields.io/badge/QuantSkills-runnable-2f6fdb?style=flat-square" alt="QuantSkills runnable">
    <img src="https://img.shields.io/badge/Python-3.10%2B-3776ab?style=flat-square&logo=python&logoColor=white" alt="Python 3.10 or newer">
    <img src="https://img.shields.io/badge/license-GPL--3.0-2ea44f?style=flat-square" alt="GPL-3.0 license">
  </p>
</div>

> 📌 **定位**：执行成本研究与回测假设校准，不从成本数据推断 alpha、交易建议或券商质量。

## 🧭 能力概览

| 能力 | 结果 |
| --- | --- |
| 成交归因 | 逐笔参考价、滑点、点差与手续费 |
| 盘口优先 | 优先使用成交时刻及之前的 quote mid |
| K 线回退 | 缺少盘口时使用成交前的 bar close |
| 冲击诊断 | 在观测参与率范围内拟合透明曲线 |

## ⚡ 快速开始

```bash
pip install -r requirements.txt
python scripts/calibrate_costs.py --demo --output-dir out
```

真实数据运行示例：

```bash
python scripts/calibrate_costs.py \
  --executions fills.csv \
  --quotes quotes.csv \
  --bars bars.csv \
  --commission-bps 2.5 \
  --output-dir cost_out
```

## 📥 输入与 📤 输出

| 数据 | 必需字段 | 说明 |
| --- | --- | --- |
| `executions.csv` | `timestamp,symbol,side,quantity,price` | `side` 为 `buy` 或 `sell` |
| `quotes.csv` | `timestamp,symbol,bid,ask` | 可选，优先作为参考价 |
| `bars.csv` | `timestamp,symbol,close,volume` | 可选，用于回退和参与率 |

输出文件：

- `execution_costs.csv`：逐笔滑点、点差、参与率、手续费和总成本。
- `cost_curve.csv`：按参与率分箱的成本中位数和 95 分位数。
- `summary.json`：覆盖率、成本分布、冲击系数和警告。

## 🔬 工作流

```text
输入契约 → UTC 时间解析 → 成交前 as-of 对齐 → 成本拆解 → 参与率曲线 → 覆盖率审阅
```

有符号滑点与绝对成本必须分开解释；冲击曲线不得超出最大观测参与率外推，除非明确写出敏感性假设。

## 🧱 边界与来源

- 仅使用允许的公开资料或用户提供的数据，详见 [`references/source_boundary.md`](references/source_boundary.md)。
- 禁止使用成交之后的报价或 K 线，禁止静默填补缺失参考价。
- 不替代组合清算压力测试或通用回测工具。

## 📁 仓库结构

```text
SKILL.md                       # Agent 工作流
scripts/calibrate_costs.py     # 确定性校准脚本
references/input_contract.md   # 输入字段与时间约束
references/source_boundary.md  # 资料边界
agents/openai.yaml             # Agent UI 元数据
agents/cursor-rule.mdc         # Cursor 运行时入口
agents/portable-loader.md      # Hermes/便携运行时入口
requirements.txt               # Python 依赖
```

## ✅ 本地校验

```bash
node scripts/validate-qsh-form.mjs SKILL.md
python scripts/calibrate_costs.py --demo --output-dir out
```

## 免责声明

本仓库仅作研究方法层面的整理，非官方、不隶属任何被研究对象，不验证任何收益声明，不构成任何投资建议。

## License

GNU General Public License v3.0，见 [LICENSE](LICENSE)。

## PandaAI / QUANTSKILLS 社群

<div align="center">
  <img src="https://raw.githubusercontent.com/quantskills/.github/main/profile/assets/pandaai-community-qr.jpg" alt="PandaAI 社群二维码" width="220">
  <br>
  <sub>扫码加入 PandaAI 社群，交流 QUANTSKILLS 技能、Agent 工作流与量化研究实践。</sub>
</div>
