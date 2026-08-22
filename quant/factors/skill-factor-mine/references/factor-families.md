# 因子族清单 —— 先确认你在哪条赛道

不要"为了挖而挖"。先想清楚你要补的是哪个**信息维度**。

## 8 大因子族（按数据可得性排序）

### Phase 1：仅量价（A 股最常用）

| 因子族 | 典型代表 | 经济含义 | 推荐窗口 |
|---|---|---|---|
| **动量 / 反转** | `mom_20 = pct_change(20) - pct_change(5)`<br/>`rev_5 = -pct_change(5)` | 行为金融（趋势 / 过度反应） | 反转 1~5d，动量 20~60d |
| **波动率 / 低波** | `-std(ret, 20)`<br/>`-(high-low)/close mean(20)` | 风险溢价异象（低波股长期跑赢） | 20~60d |
| **流动性** | `-amihud = -mean(\|ret\|/amount)`<br/>`-turnover_20`<br/>`-log(market_cap)` | 流动性溢价 | 20~120d |
| **量价相关 / 量能** | `corr(close, vol, 20)`<br/>`-vol_cv = -std(vol)/mean(vol)` | 信息含量 / 散户机构结构 | 20~120d |
| **形态 / lottery** | `-max(ret, 20)` (MAX 因子)<br/>`-skew(ret, 60)`<br/>`gap_open = open/prev_close - 1` | lottery preference（彩票偏好让正偏股被高估） | 20~120d |

### Phase 2：基本面（需要财务数据）

| 因子族 | 典型代表 | 经济含义 |
|---|---|---|
| **估值** | EP, BP, SP, EV/EBITDA | 估值回归 |
| **盈利质量** | ROE, ROA, gross_margin, accruals | 质量溢价 |
| **成长** | YoY revenue / earnings growth | 增长溢价 |

### Phase 3：另类数据

| 因子族 | 典型代表 | 经济含义 |
|---|---|---|
| **高频** | intraday flow, order imbalance | 市场微结构 |
| **舆情** | news sentiment, analyst revision | 信息扩散 |

## 经验门槛

- **两两相关性 < 0.6** 是经验门槛
- **> 0.85** 视为同质化（要么删要么并）— 见 `correlation-gate.md`
- **理想因子库**：8 个因子，覆盖 4~6 个族，平均 |ρ| < 0.30

## 决策树：下一个该挖什么

```
当前 FACTORS 是什么族分布？
├─ 全在 1 个族 → 换族（最缺哪个就挖哪个）
├─ 覆盖 2~3 族 → 补 1 个空缺族
├─ 覆盖 4+ 族但平均 |ρ| > 0.4 → 删同质，不要继续加
└─ 覆盖 5+ 族且 |ρ| < 0.3 → 该换 combine_method（IC_IR / Ridge / LGBM）了
```

## 反偏好

| ❌ 别做 | ✅ 改做 |
|---|---|
| 同族堆 5 个（5 日反转 + 3 日反转 + 10 日反转 + ...） | 选 1 个代表，换族 |
| 50 行复杂特征工程换 0.005 IC | 5~20 行物理含义清晰的简单因子 |
| 纯统计搜索"幸存者"（grid search 出来的因子） | 有经济 / 行为金融解释的因子 |

> 参考实现：`auto_research_alpha/program.md §3, §5`。
