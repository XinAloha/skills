<div align="center">
  <h1>预测校准审计</h1>
  <p>判断概率预测是否可信，而不只看它能否把样本排序正确。</p>
  <p>
    <a href="README.en.md">English</a>
    ·
    <a href="https://github.com/quantskills/skill-forecast-calibration-audit/issues">反馈问题</a>
  </p>
  <p>
    <img src="https://img.shields.io/badge/QuantSkills-runnable-2f6fdb?style=flat-square" alt="QuantSkills runnable">
    <img src="https://img.shields.io/badge/Python-3.10%2B-3776ab?style=flat-square&logo=python&logoColor=white" alt="Python 3.10 or newer">
    <img src="https://img.shields.io/badge/license-GPL--3.0-2ea44f?style=flat-square" alt="GPL-3.0 license">
  </p>
</div>

> 📌 **定位**：概率预测质量审计，覆盖可靠性、评分、阈值表现和时间漂移；不构成投资建议。

## 🧭 能力概览

| 能力 | 结果 |
| --- | --- |
| 可靠性分析 | 概率分箱、实际发生率、偏差和加权偏差 |
| 适当评分 | Brier Score 与裁剪后的 Log Loss |
| 校准诊断 | 截距、斜率、ECE/MCE |
| 时间审计 | 连续时间切片、类别平衡和漂移警告 |

## ⚡ 快速开始

```bash
pip install -r requirements.txt
python scripts/calibrate_forecasts.py --demo --output-dir out
```

真实数据运行示例：

```bash
python scripts/calibrate_forecasts.py \
  --input forecasts.csv \
  --output-dir calibration_out \
  --threshold 0.5 \
  --time-bins 5
```

## 📥 输入与 📤 输出

| 数据 | 必需字段 | 说明 |
| --- | --- | --- |
| `forecasts.csv` | `date,probability,outcome` | 概率在 `[0,1]`，结果为 `0/1` |
| 分组信息 | 可选 `regime` 或 `--regime-column` | 用于子组诊断 |

输出文件：

- `scored_predictions.csv`：原始预测及逐行 Brier/Log Loss 项。
- `reliability.csv`：概率分箱、预测均值、实际发生率和偏差。
- `time_metrics.csv`：按时间切片的校准指标。
- `summary.json`：总体指标、校准系数、类别比例和警告。

## 🔬 工作流

```text
输入契约 → 概率/标签检查 → 按时间排序 → 连续分箱 → 评分与校准 → 时间漂移审阅
```

概率只在 Log Loss 的内部计算中裁剪，原始概率会保留在评分输出中。小分箱必须结合样本量、日期范围和类别平衡解释；重新校准时应使用更早窗口训练、更晚窗口验证。

## 🧱 边界与来源

- 仅使用允许的公开资料或用户提供的数据，详见 [`references/source_boundary.md`](references/source_boundary.md)。
- 不随机打乱时间序列，不把完美小样本分数解释为泛化能力。
- 不替代因子评价、IC 分析或事件跟踪工具。

## 📁 仓库结构

```text
SKILL.md                        # Agent 工作流
scripts/calibrate_forecasts.py  # 确定性审计脚本
references/input_contract.md    # 输入字段与校验规则
references/source_boundary.md   # 资料边界
agents/openai.yaml              # Agent UI 元数据
agents/cursor-rule.mdc          # Cursor 运行时入口
agents/portable-loader.md       # Hermes/便携运行时入口
requirements.txt                # Python 依赖
```

## ✅ 本地校验

```bash
node scripts/validate-qsh-form.mjs SKILL.md
python scripts/calibrate_forecasts.py --demo --output-dir out
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
