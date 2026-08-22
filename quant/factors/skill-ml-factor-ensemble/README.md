# 🧩 ML Factor Ensemble · 机器学习因子合成器

**简体中文** | [English](README.en.md)

> 把上百个已有因子，用「防泄漏」的滚动窗口监督合成为一个样本外 meta-alpha。

![type](https://img.shields.io/badge/type-agent--skill-blue)
![license](https://img.shields.io/badge/license-GPLv3-blue)
![validation](https://img.shields.io/badge/validation-Runnable-orange)

---

## 📖 这是什么

社区有 800+ 个因子，但缺一个「把它们合成一个信号」的监督学习层。本 skill 输入
`date, symbol, <因子列>, fwd_ret` 的长面板，输出一个**只含样本外预测**的合成信号，
并给出特征重要性、对等权基线的 ICIR 提升。

它和已有仓库的区别很清晰：

- 不同于 `skill-factormad-debate-factor-mining`（LLM 辩论**造新公式**）—— 本 skill 是
  监督学习**合成已有因子**。
- 不同于 `skill-factor-evaluate`（评**单个**因子）—— 本 skill 学**多因子加权**。

**核心卖点是防泄漏**：滚动 walk-forward + Purging + Embargo（López de Prado）。
朴素 K-fold 在重叠前瞻标签上会严重高估表现，本 skill 从 fold 构建层面杜绝。

## 🚀 快速开始

```bash
cp -r skill-ml-factor-ensemble ~/.claude/skills/ml-factor-ensemble
pip install -r requirements.txt
# 玩具数据自检（无需凭证/lightgbm）
python scripts/ml_ensemble.py --model ridge --horizon 5
python scripts/test_ml_ensemble.py
```

真实数据：

```bash
python scripts/ml_ensemble.py \
  --panel-csv panel.csv --factors f_mom,f_rev,f_vol,f_liq \
  --model lightgbm --horizon 5 --train-window 252 \
  --out combined_signal.csv --report ensemble_report.md
```

历史长度不足 `--train-window` 时，CLI 会生成带表头的空信号文件和明确降级原因的
`ensemble_report.md`，不会在 ICIR 计算阶段崩溃。ElasticNet 可用
`--elasticnet-alpha` / `--elasticnet-l1-ratio` 调整正则强度。

```text
触发示例 prompt：
「把这 50 个因子无泄漏地合成一个信号，告诉我哪些真正有用，并和等权基线比 ICIR」
「用 LightGBM 学因子间的非线性交互，做 5 日前瞻的样本外合成」
```

## 📦 目录结构

```text
skill-ml-factor-ensemble/
├── SKILL.md
├── requirements.txt
├── references/
│   ├── leakage-control.md       # purge/embargo 数学 + fold 构建 + 泄漏陷阱
│   └── source_boundary.md
├── scripts/
│   ├── ml_ensemble.py           # 核心: make_walkforward_folds + walk_forward_predict + 评估
│   ├── test_ml_ensemble.py      # 净化/样本外冒烟测试
│   └── login_pandadata.py
└── agents/
    └── openai.yaml
```

## 📐 核心约束

| 约束 | 说明 |
| --- | --- |
| 🧪 防泄漏第一 | 滚动 walk-forward + purge(H) + embargo，H 必须匹配真实标签前瞻期 |
| 📊 必比基线 | 永远对比「等权 zscore 因子」基线，打不过就说明没学到信息 |
| ⬆️ ICIR 是上界 | OOS≠实盘，幸存者偏差/多重检验仍会高估 |
| 🚫 只述不荐 | 合成信号是研究产物，不构成任何投资建议 |

## ✅ 真实数据测试结论（2026-07-27）

- **smoke test**：`python scripts/test_ml_ensemble.py` 全部通过（需 scikit-learn；LightGBM 可选，缺失时回退 Ridge/ElasticNet）。
- **数据依赖**：输入是「因子面板 + 前瞻收益」，为纯本地监督学习（Purged & Embargoed walk-forward），不绑定特定 Pandadata 接口——上游因子可来自组织任意因子技能或 `get_factor`。
- 结论：代码可靠，无外部数据可得性风险；运行需 numpy / pandas / scikit-learn。

## ⚠️ 免责声明

本仓库仅提供因子合成的研究方法与代码骨架，不下单、不验证任何收益声明、不构成任何投资建议。
默认 Community Project；请结合引用的数据与本地审核要求复核输出。

## 📜 License

GPL-3.0-only，详见 [LICENSE](LICENSE)。

## 🐼 PandaAI / QUANTSKILLS 社群

<div align="center">
  <img src="https://raw.githubusercontent.com/quantskills/.github/main/profile/assets/pandaai-community-qr.jpg" alt="PandaAI 社群二维码" width="220">
  <br>
  <sub>扫码加入 PandaAI 社群，交流 QUANTSKILLS 技能、Agent 工作流与量化研究实践。</sub>
</div>
