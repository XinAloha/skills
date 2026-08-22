# 因子相关性过高

## 症状

```
PermissionError: 因子相关性 ρ=0.91 (>= 0.85) with f_reversal_5
```

## 原因

新因子和已有因子高度相关 —— 加了等于没加，反而增加共线性。门控阈值：

| \|ρ\| | 行为 |
|---|---|
| ≥ 0.85 | CRASH，必须改设计 |
| 0.60 ~ 0.85 | 警告但允许 |
| < 0.60 | 静默通过 |

## 改设计的 3 个方向

### 方向 1：换计算方式

```python
# ❌ 与已有 vol_20 高相关
def f_volatility_60(panel):
    return -panel["close"].pct_change().rolling(60).std()

# ✅ 改用相对波动（vol_20 / vol_120）
def f_relative_vol(panel):
    ret = panel["close"].pct_change()
    return -ret.rolling(20).std() / ret.rolling(120).std()
```

### 方向 2：换输入

```python
# ❌ 与已有 reversal_5（基于 close）高相关
def f_reversal_5_v2(panel):
    return -panel["close"].pct_change(5)  # 重复

# ✅ 改用 vwap
def f_reversal_5_vwap(panel):
    vwap = (panel["close"] * panel["volume"]).rolling(5).sum() / panel["volume"].rolling(5).sum()
    return -vwap.pct_change(5)
```

### 方向 3：换横截面定义

```python
# ❌ 全市场 momentum 与已有相关
def f_momentum_20(panel):
    return panel["close"].pct_change(20)

# ✅ 改用行业内 z-score
def f_momentum_20_industry_neutral(panel, industry):
    raw = panel["close"].pct_change(20)
    # 行业内 z-score
    return raw.groupby(industry).transform(lambda x: (x - x.mean()) / x.std())
```

## 何时绕过门控

如果你确信高相关因子有**独立价值**（如做风险因子做对冲），改 op_type：

```python
ITER_NOTE = {
    "op_type": "combine_method",   # 不是 add_factor
    ...
}
```

在组合层面专门处理（GLS 残差化 / 因子正交化），而不是当 alpha 因子加。

## 反模式

- ❌ 加 `# noqa` 注释绕过门控
- ❌ 把因子值乘以 1.001 假装是新因子
- ❌ 改个名字（`f_rev_5_v2` ≈ `f_reversal_5`）
- ❌ 把高相关因子拆成两个低相关组件再加 —— 仍然提供相同信息

## 用门控做研究

门控本身就是研究工具：

```python
# 算因子库相关性矩阵，找潜在的同质化
corr_matrix = factor_correlation(FACTORS)
high_corr_pairs = []
for i, fi in enumerate(FACTORS):
    for j, fj in enumerate(FACTORS[i+1:], i+1):
        if abs(corr_matrix.iloc[i, j]) > 0.5:
            high_corr_pairs.append((fi.__name__, fj.__name__, corr_matrix.iloc[i, j]))
```

如果发现 |ρ| > 0.5 的对，考虑删一个保一个，让因子库更"瘦"。
