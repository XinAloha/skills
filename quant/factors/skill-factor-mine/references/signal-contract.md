# 信号契约 —— 截面研究的硬门禁

`alpha.run(train, val) -> (signal_train, signal_val)` 返回的两份信号必须满足这些约束。违反 = runner 直接判失败，不会进入评分。

## 形态约束

| 约束 | 阈值 |
|---|---|
| shape | `[date × symbol]` 二维 DataFrame |
| index | `pd.DatetimeIndex`，单调升序 |
| columns | symbol 字符串 |
| dtype | float（int / object 一律拒绝）|

## 数值约束

| 约束 | 阈值 | 含义 |
|---|---|---|
| 截面规模 | 每日非 NaN 列数 ≥ 30 | 太少没有 IC 显著性 |
| 截面均值 | `mean(\|daily_mean\|) < 0.05` | 信号已去市场均值 |
| 截面 std | `0.5 < mean(daily_std) < 2.0` | 信号已 z-score |
| 全 NaN 行占比 | < 50% | 数据质量底线 |

## 通用实现：截面 winsorize + z-score

```python
import numpy as np
import pandas as pd

def cs_winsorize_zscore(f: pd.DataFrame, n_mad: float = 3.0) -> pd.DataFrame:
    """每日截面独立做 MAD winsorize + z-score。

    用 MAD 而非 std 来 winsorize：抗极端值，A 股 ST/借壳/复牌等
    异常更稳健。
    """
    med = f.median(axis=1)
    mad = (f.sub(med, axis=0)).abs().median(axis=1)
    sigma = 1.4826 * mad
    upper = med + n_mad * sigma
    lower = med - n_mad * sigma
    f_clip = f.clip(lower=lower, upper=upper, axis=0)

    mu = f_clip.mean(axis=1)
    sd = f_clip.std(axis=1).replace(0, np.nan)
    return f_clip.sub(mu, axis=0).div(sd, axis=0)
```

## 调用规则

1. **每个单因子**进入组合前必做一次（L1）
2. **最终组合信号**返回前**再做一次**（L2）—— 保证组合后仍满足截面约束
3. **不要做时序标准化** —— 违反"纯截面"范式，引入未来信息

## 参数调优

| n_mad | 用途 |
|---|---|
| 1.5 | 严格 winsorize，A 股 ST 多时（推荐 baseline） |
| 3.0 | 标准 winsorize，主流场景 |
| 5.0 | 弱 winsorize，因子本身分布较好（如已经 rank） |

## 失败对照表

| 报错 | 病因 | 修复 |
|---|---|---|
| `截面均值超阈值 \|mean(daily_mean)\|=0.082` | 没去截面均值 | 加 `f.sub(f.mean(axis=1), axis=0)` |
| `截面 std 不在 [0.5, 2.0]: 0.31` | winsorize 太严，截到平 | n_mad 从 1.5 → 3.0 |
| `截面 std=0` | 因子全相同（lookback 太长，前期全 NaN） | 增加 `min_periods` 或缩短窗口 |
| `截面规模 < 30` | 因子需要长 lookback，早期数据全 NaN | 截掉 panel 早期段 |

> 参考实现：`auto_research_alpha/prepare.py:validate_signal()` + `evaluation.md §6`。
