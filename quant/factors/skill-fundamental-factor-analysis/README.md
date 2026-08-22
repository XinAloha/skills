# Fundamental Factor Analysis — README

## 一句话

计算、验证和分析 A 股基本面因子。从季度财报中提取估值、质量、成长因子，并通过 IC 分析、分组收益和 Fama-MacBeth 回归进行系统性验证。

## 为什么需要这个 Skill

QUANTSKILLS 目前拥有 800+ 个 OHLCV（量价）因子 Skill，**零基本面因子**。本 Skill 填补了这个空白。

## 核心功能

### 因子计算
- **估值因子**: EP, BP, SP, CP, FCFP, GP/A — 全部以"倒数"形式计算（越高 = 越低估）
- **质量因子**: ROE, ROA, 毛利率, 营业利润率, 应计利润, 杠杆率 — 识别高质量公司
- **成长因子**: 盈利增长, 营收增长, ROE 增长 — 捕捉加速增长
- **复合因子**: Piotroski F-Score, Quality Minus Junk, PEG, GARP, Value+Quality

### 因子验证
- Rank IC 分析（均值、IR、t-stat、正向比例）
- 十档分组收益（单调性、多空 spread）
- Fama-MacBeth 截面回归（含控制变量）
- IC 衰减曲线与半衰期计算
- 子样本稳定性检验

### 数据来源

使用 Pandadata API:
- `panda_data.get_fina_performance()` — 财务快报（30+ 字段）
- `panda_data.get_fina_reports()` — 详细财报（100+ 字段）
- `panda_data.get_factor()` — 日频数据 + `market_cap`
- `panda_data.get_market_data()` — 量价日线

## 目录

```
skill-fundamental-factor-analysis/
├── SKILL.md                    ← 核心工作流 + 完整代码
├── README.md                   ← 本文件
├── README.en.md
├── LICENSE
├── .gitignore
├── references/
│   ├── factor_definitions.md   ← 16种因子完整定义、公式、边界情况
│   ├── composite_factors.md    ← F-Score/QMJ/PEG等复合因子
│   ├── validation_report.md    ← 验证报告模板和诊断
│   ├── accounting_notes.md     ← 特殊会计处理（金融/ST/IPO/时滞）
│   └── source_boundary.md
├── agents/
│   └── openai.yaml
└── examples/
    ├── value_factor_analysis.py
    ├── quality_factor_rotation.py
    ├── f_score_pipeline.py
    └── composite_factor.py
```

## 使用方式

```
"对沪深300成分股计算 EP 因子，做 IC 分析和分组收益"
"构建一个 ROE+毛利率复合质量因子，做 Fama-MacBeth 回归"
"计算全 A 股的 Piotroski F-Score，高分组 vs 低分组对比"
"验证 BP 因子的 IC 衰减曲线，最佳再平衡频率是多少"
```
