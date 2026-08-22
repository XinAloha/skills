# Layer 2：结构分析

复盘的第二层 —— 把"为什么是这个 best"拆开看。

## 三个核心分析

### §2.1 因子族分布

把当前 best alpha.py 的 FACTORS 按族归类：

```
=== 当前 FACTORS（best, 6 个）===
反转 / 动量族  : []                  ← 0 个，缺
波动率族       : []                  ← 0 个，缺
流动性族       : [size_inv]
形态 / lottery : [neg_max_ret_120]
量能分布       : [neg_vol_cv_120]
量价相关       : []                  ← 0 个，缺
```

**预警**：因子族越偏（如 6 个全是 lottery），策略风格越极端，市场风格切换时崩盘。

实现：

```python
FAMILY_KEYWORDS = {
    "反转/动量": ["reversal", "rev_", "momentum", "mom_", "trend"],
    "波动率":   ["vol_", "volatility", "hl_range", "atr"],
    "流动性":   ["amihud", "turnover", "size", "illiq", "liquidity"],
    "形态":     ["max_ret", "skew", "gap_", "lottery", "min_ret"],
    "量能分布": ["vol_cv", "volume_skew", "amount_"],
    "量价相关": ["corr_", "price_volume", "divergence"],
    "估值":     ["ep", "bp", "sp", "ev_"],
    "盈利质量": ["roe", "roa", "margin", "accruals"],
}

def classify_factor(name: str) -> str:
    for fam, kws in FAMILY_KEYWORDS.items():
        if any(kw in name.lower() for kw in kws):
            return fam
    return "其他"
```

### §2.2 相关性矩阵

跑一遍当前所有因子的两两 spearman ρ：

```python
def factor_correlation_matrix(factors: list[pd.DataFrame], names: list[str]) -> pd.DataFrame:
    n = len(factors)
    M = np.zeros((n, n))
    for i in range(n):
        for j in range(i, n):
            x = factors[i].rank(axis=1).values.flatten()
            y = factors[j].rank(axis=1).values.flatten()
            mask = ~(np.isnan(x) | np.isnan(y))
            if mask.sum() < 100:
                M[i, j] = M[j, i] = np.nan
            else:
                rho = np.corrcoef(x[mask], y[mask])[0, 1]
                M[i, j] = M[j, i] = rho
    return pd.DataFrame(M, index=names, columns=names)
```

输出表格：

```
              size  max120  vol_cv
size          1.00   0.42   0.31
max120        0.42   1.00   0.55     ← 0.55 警告区
vol_cv        0.31   0.55   1.00
```

**判读**：

| 平均 \|ρ\| | 含义 |
|---|---|
| < 0.30 | 因子库多样化健康 |
| 0.30 ~ 0.50 | 中等同质化，可接受 |
| > 0.50 | 严重同质化，删几个或重设计 |

### §2.3 最优路径回溯

按实验日志找出**通往当前 best 的关键决策**：

```
=== Path to best (+0.63) ===
[bottleneck breaks]
  Iter 04: +amihud           → +0.18  (流动性族切入)
  Iter 17: HORIZON 5→20      → +0.42  (周期适配)
  Iter 28: +max_ret_60       → +0.56  (lottery 大幅提分)
  Iter 44: +vol_cv_120       → +0.61  (量能分布族开张)

[noise / 平台期]
  Iter 05-08, 18-21, 29-43 大量小幅迭代（+0.02 以内）
  其中 ACCEPTED 仅 3 / 47，多为细微 winsorize / 阈值微调

启示：
  - "突破"基本来自换族 / 换 horizon，不来自微调
  - 30+ 轮的 micro-iteration 性价比低
```

## 实现

```python
def trace_best_path(runs: pd.DataFrame, threshold: float = 0.05) -> pd.DataFrame:
    """提取分数大跳跃（≥ threshold）的关键决策。"""
    accepted = runs[runs["status"] == "ACCEPTED"].sort_values("iter").reset_index(drop=True)
    accepted["delta"] = accepted["score"].diff()
    breakthroughs = accepted[accepted["delta"] >= threshold]
    return breakthroughs[["iter", "name", "op_type", "score", "delta", "hypothesis"]]
```

## 综合输出

每一层的核心结论要在 Layer 3 里被引用，形成"基于 Layer 2 的发现 → Layer 3 给假设"的因果链。

例如：
- Layer 2 §2.1 发现"反转族空缺" → Layer 3 推荐"加 f_reversal_5"
- Layer 2 §2.2 发现"max_ret 与 vol_cv ρ=0.55" → Layer 3 警告"不要再加 lottery 因子"
- Layer 2 §2.3 发现"突破来自换族不是微调" → Layer 3 推荐"做 phase transition"
