# 子样本 IC — 看在哪类股票上有效

**整体 IC = 0.04** 可能是**小票 IC=0.08，大票 IC=0**，也可能是**全样本平均 0.04**。两者后续策略完全不同。

## 三个核心维度

### 1. 按市值分组（最重要）

```python
def ic_by_size(signal: pd.DataFrame, fwd_ret: pd.DataFrame,
               size_proxy: pd.DataFrame, n_groups: int = 5) -> pd.DataFrame:
    """size_proxy 可用 close * 流通股本 或 log(amount) 滚动均值。"""
    size_rank = size_proxy.rank(axis=1, pct=True)
    rows = []
    for q in range(n_groups):
        lo, hi = q / n_groups, (q + 1) / n_groups
        mask = (size_rank > lo) & (size_rank <= hi)
        sig_q = signal.where(mask)
        ret_q = fwd_ret.where(mask)
        ic = _xs_corr(sig_q.rank(axis=1), ret_q.rank(axis=1))
        rows.append({
            "size_group": f"Q{q+1}" + (" (smallest)" if q == 0 else " (largest)" if q == n_groups - 1 else ""),
            "ic_mean":    float(ic.mean()),
            "ic_ir":      float(ic.mean() / ic.std() * np.sqrt(252)),
        })
    return pd.DataFrame(rows)
```

### 2. 按波动率分组

```python
def ic_by_volatility(signal, fwd_ret, panel, n_groups=5, vol_window=20):
    close = panel.pivot(index="date", columns="symbol", values="close").sort_index()
    vol = close.pct_change().rolling(vol_window).std()
    return _ic_by_factor_proxy(signal, fwd_ret, vol, n_groups, "vol_group")
```

### 3. 按行业分组（如果有数据）

```python
def ic_by_industry(signal, fwd_ret, industry_map: pd.Series):
    """industry_map: index=symbol, values=industry name"""
    rows = []
    for ind in industry_map.unique():
        syms = industry_map[industry_map == ind].index
        sig_i = signal.reindex(columns=syms)
        ret_i = fwd_ret.reindex(columns=syms)
        ic = _xs_corr(sig_i.rank(axis=1), ret_i.rank(axis=1))
        rows.append({
            "industry":  ind,
            "n_stocks":  len(syms),
            "ic_mean":   float(ic.mean()),
            "ic_ir":     float(ic.mean() / ic.std() * np.sqrt(252)),
        })
    return pd.DataFrame(rows).sort_values("ic_mean", ascending=False)
```

## 解读模板

| 模式 | 解读 | 行动 |
|---|---|---|
| **小市值 IC 强、大市值 IC 弱** | 因子吃流动性溢价 | 实盘容量受限于小盘流动性，组合规模上限明确 |
| **高波 IC 强、低波 IC 弱** | 因子吃风险溢价 | 实盘多头组合 MDD 会大，考虑波动率中性 |
| **行业 IC 极端分化** | 因子带强行业 bias | 做行业中性化（每行业内独立 z-score）|
| **各组 IC 接近** | 因子稳健，跨子样本一致 | 健康，可放心组合 |
| **大市值 IC 强** | 罕见但好 | 容量大，机构友好 |

## 实操建议

1. **市值切分必做** —— A 股因子最常见的"假效"是只在小票上有效
2. 波动率切分二优先
3. 行业切分有数据就做（Phase 2）
4. **不要按时间切分**做子样本（"2020 年 IC 高、2022 年低"）—— 这是 IC timeline 的工作，不是子样本

## 反模式

- ❌ 不切子样本，整体 IC=0.04 就直接说"因子有效"
- ❌ 用未来的市值（如 2026 年的 close * shares）切 2021 年 —— 偷看未来
- ❌ 按 signal 自己分组（"high signal 组 IC 怎么样"） —— 套套逻辑
