"""横截面行业 + 风格中性化（B10 内部模块）。

把因子值按"行业（one-hot dummies）+ 风格因子（z-score）"做横截面回归取残差，
把行业暴露与规模/流动性等系统性风险源剥离掉，剩下的横截面排序信息进 B10 评估。

红线
- B10 不联网。所有行业/风格暴露面板必须由调用方在 ``config["industry_panel"]`` /
  ``config["style_panel"]`` 中传入，或预先合并到 B10 标准面板的同名风格列里。
  开启 ``neutralize=True`` 但既没传 industry/style 暴露面板、面板里也没有风格列时，
  ``apply_neutralization`` 抛 ``ValueError`` 让调用方明确补齐数据。
- 行业/风格的获取由外部桥接层负责，不在 B10 内做任何 PandaAI data 调用。

关键约束
- 中性化是**横截面**的：对每个 trade_date 独立拟合，不跨日泄露未来信息。
- 残差与原始 factor 同尺度（mean=0），不会改变 RankIC 的方向语义；只会改变
  "因子来源于行业 / 规模"那部分被剥离的能力，是评估提纯而非操纵。
- 只对 ``factor_value`` 做中性化，``forward_return`` 保持原样；中性化对象是因子，
  不是收益。这样 IC = corr(neutralized_factor, forward_return) 的解读最直观。
- 缺失风格列填 0（"中性暴露"）；缺失行业归类入 ``__unknown__`` 桶。
- 不依赖 statsmodels；用 ``numpy.linalg.lstsq`` 求最小二乘解。

数学
对每个 trade_date d，构造设计矩阵 X = [1, industry_dummies, z(style)...]，
解 ``y = factor_value`` 的 OLS：``β = (X^T X)^{-1} X^T y``，
取残差 ``e = y - Xβ`` 作为中性化因子。Winsorize 在前，z-score 在后。
"""

from __future__ import annotations

from typing import Any, Sequence

import numpy as np
import pandas as pd


DEFAULT_STYLE_FACTORS = ("log_market_cap", "turnover")


def winsorize(values: pd.Series, limits: float = 0.01) -> pd.Series:
    """两端按分位数做缩尾，抑制极端值对 OLS 的拉扯。"""
    s = pd.to_numeric(values, errors="coerce")
    if s.notna().sum() == 0:
        return s
    lower = s.quantile(limits)
    upper = s.quantile(1 - limits)
    return s.clip(lower=lower, upper=upper)


def zscore(values: pd.Series) -> pd.Series:
    """横截面标准化。常数列返回全 0。"""
    s = pd.to_numeric(values, errors="coerce")
    std = s.std(ddof=0)
    if not std or not np.isfinite(std):
        return pd.Series(np.zeros(len(s)), index=s.index)
    return (s - s.mean()) / std


def _build_style_panel(
    panel: pd.DataFrame,
    style_columns: Sequence[str],
) -> pd.DataFrame:
    """把上游已经放进 panel 的风格列拿出来，缺失的用 NaN 占位。"""
    cols = ["trade_date", "ts_code", *style_columns]
    have = [c for c in cols if c in panel.columns]
    out = panel[have].copy()
    for col in style_columns:
        if col not in out.columns:
            out[col] = np.nan
    return out[cols]


def _normalize_exposure_keys(frame: pd.DataFrame, required_extra: Sequence[str] = ()) -> pd.DataFrame:
    """调用方传入的暴露面板可能保留 datetime/code 空格；进入 merge 前统一到 B10 主键口径。"""
    out = frame.copy()
    required = {"trade_date", "ts_code", *required_extra}
    missing = required - set(out.columns)
    if missing:
        raise ValueError(f"中性化暴露面板缺少必要字段: {sorted(missing)}")
    parsed_dates = pd.to_datetime(out["trade_date"], errors="coerce")
    if parsed_dates.isna().any():
        raise ValueError(f"中性化暴露面板 trade_date 存在无法解析的日期值，异常行数: {int(parsed_dates.isna().sum())}")
    out["trade_date"] = parsed_dates.dt.strftime("%Y-%m-%d")
    out["ts_code"] = out["ts_code"].astype(str).str.strip()
    if out["ts_code"].eq("").any():
        raise ValueError("中性化暴露面板 ts_code 不能为空")
    return out


def _ols_residuals(y: np.ndarray, X: np.ndarray) -> np.ndarray:
    """``y - X β`` 的残差。X 病态/秩亏时自动用 lstsq 的最小范数解，残差仍有定义。"""
    if X.shape[1] == 0:
        return y - y.mean()
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    return y - X @ beta


def neutralize_cross_section(
    panel: pd.DataFrame,
    industry_panel: pd.DataFrame | None = None,
    style_panel: pd.DataFrame | None = None,
    style_factors: Sequence[str] = DEFAULT_STYLE_FACTORS,
    factor_col: str = "factor_value",
    winsorize_limits: float = 0.01,
) -> pd.DataFrame:
    """对 ``factor_col`` 做行业 + 风格中性化，把残差写回同名列。

    Args:
        panel: B10 标准评价面板（已 validate）。
        industry_panel: ``[trade_date, ts_code, industry]``，缺则不做行业剥离。
        style_panel: ``[trade_date, ts_code, *style_factors]``，缺则不做风格剥离。
        style_factors: 实际参与中性化的风格列名集合。
        factor_col: 要中性化的列。默认 ``factor_value``。
        winsorize_limits: 风格因子 winsorize 的上下分位数（0.01 表示 1%/99%）。

    Returns:
        新 panel，``factor_col`` 已替换为日内中性化残差；附带 ``__neutralize_meta__``
        attrs，记录每天有多少行业 / 风格列实际参与回归，供质量诊断。
    """
    if panel.empty:
        return panel.copy()

    base_cols = list(panel.columns)
    out = panel.copy()
    out["__factor_raw__"] = pd.to_numeric(out[factor_col], errors="coerce")

    # 行业 / 风格按 (trade_date, ts_code) 左连接
    if industry_panel is not None and not industry_panel.empty:
        industry_panel = _normalize_exposure_keys(industry_panel, required_extra=["industry"])
        out = out.merge(industry_panel, on=["trade_date", "ts_code"], how="left")
    else:
        out["industry"] = "__unknown__"
    if style_panel is not None and not style_panel.empty:
        style_panel = _normalize_exposure_keys(style_panel)
        out = out.merge(style_panel, on=["trade_date", "ts_code"], how="left")

    # 缺失风格列的占位（保持后续 indexing 不炸）
    used_styles = [c for c in style_factors if c in out.columns]

    daily_meta: list[dict[str, Any]] = []
    new_factor = pd.Series(np.nan, index=out.index, dtype=float)

    for trade_date, day in out.groupby("trade_date", sort=False):
        idx = day.index
        y = pd.to_numeric(day["__factor_raw__"], errors="coerce").to_numpy(dtype=float)
        valid = np.isfinite(y)
        if valid.sum() < 3:
            # 截面太小，原样返回
            new_factor.loc[idx] = pd.to_numeric(day[factor_col], errors="coerce").to_numpy(dtype=float)
            daily_meta.append({"trade_date": str(trade_date), "n": int(valid.sum()), "industries": 0, "styles": 0, "skipped": True})
            continue

        # 行业 dummies（drop_first 避免 X 与截距共线）
        industries = day["industry"].fillna("__unknown__").astype(str)
        industry_dummies = pd.get_dummies(industries, prefix="ind", drop_first=True).astype(float)

        # 风格因子：winsorize → z-score；缺失填 0（即"中性暴露"）
        style_block = pd.DataFrame(index=day.index)
        n_styles_used = 0
        for col in used_styles:
            raw = pd.to_numeric(day[col], errors="coerce")
            if raw.notna().sum() < 3:
                continue
            wz = zscore(winsorize(raw, limits=winsorize_limits)).fillna(0.0)
            style_block[col] = wz.to_numpy()
            n_styles_used += 1

        # 设计矩阵：[1, industry_dummies..., styles...]
        intercept = np.ones((len(day), 1), dtype=float)
        parts = [intercept]
        if not industry_dummies.empty:
            parts.append(industry_dummies.to_numpy(dtype=float))
        if not style_block.empty:
            parts.append(style_block.to_numpy(dtype=float))
        X = np.concatenate(parts, axis=1)

        y_filled = np.where(valid, y, 0.0)
        # 仅对 valid 行解 OLS，避免 NaN 拖跨 lstsq
        X_valid = X[valid]
        y_valid = y_filled[valid]
        try:
            resid_valid = _ols_residuals(y_valid, X_valid)
        except np.linalg.LinAlgError:
            resid_valid = y_valid - y_valid.mean()

        resid_full = np.full(len(day), np.nan, dtype=float)
        resid_full[valid] = resid_valid
        new_factor.loc[idx] = resid_full
        daily_meta.append(
            {
                "trade_date": str(trade_date),
                "n": int(valid.sum()),
                "industries": int(industry_dummies.shape[1]),
                "styles": int(n_styles_used),
                "skipped": False,
            }
        )

    out[factor_col] = new_factor
    out = out[base_cols].copy()

    out.attrs.update(panel.attrs)
    out.attrs["neutralize_meta"] = daily_meta
    out.attrs["neutralize_style_columns"] = list(used_styles)
    out.attrs["neutralize_industry_levels"] = (
        sorted({m["industries"] for m in daily_meta}) if daily_meta else []
    )
    return out


def apply_neutralization(panel: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    """根据 config 决策是否做中性化，返回中性化后的 panel。

    config 关键字
    - ``neutralize`` (bool, 默认 False)：总开关。
    - ``neutralize_industry`` (bool, 默认 True)：是否使用行业暴露。
    - ``neutralize_style`` (Sequence[str] | None)：风格因子列；None 走默认。
    - ``industry_panel`` (DataFrame | None)：``[trade_date, ts_code, industry]``。
    - ``style_panel`` (DataFrame | None)：``[trade_date, ts_code, *neutralize_style]``。

    红线
    - B10 不联网。``industry_panel`` / ``style_panel`` 必须由调用方传入，
      或在 B10 标准面板里自带同名风格列；缺少时直接 ``ValueError``，
      不再尝试调用 PandaAI data 之类的外部数据接口。
    """
    if not bool(config.get("neutralize", False)):
        return panel

    industry_panel = config.get("industry_panel")
    style_panel = config.get("style_panel")
    use_industry = bool(config.get("neutralize_industry", True))
    style_factors: Sequence[str] = tuple(config.get("neutralize_style") or DEFAULT_STYLE_FACTORS)

    # 风格优先用调用方面板里自带的同名列；否则使用 style_panel 显式传入
    builtin_style = _build_style_panel(panel, style_factors)
    has_builtin_style = bool(style_factors) and builtin_style[list(style_factors)].notna().any().any()
    if style_panel is None and has_builtin_style:
        style_panel = builtin_style

    if use_industry and (industry_panel is None or (
        isinstance(industry_panel, pd.DataFrame) and industry_panel.empty
    )):
        raise ValueError(
            "neutralize=True 但未传入 industry_panel。B10 不联网拉行业，"
            "请在 config['industry_panel'] 中提供 [trade_date, ts_code, industry] 暴露面板，"
            "或将 config['neutralize_industry'] 显式设为 False。"
        )
    if style_factors and (style_panel is None or (
        isinstance(style_panel, pd.DataFrame) and style_panel.empty
    )):
        raise ValueError(
            "neutralize=True 但未传入 style_panel，且面板内也没有 "
            f"{list(style_factors)} 中的任何风格列。B10 不联网拉风格，"
            "请在 config['style_panel'] 中提供风格暴露面板，或在输入面板中自带同名列，"
            "或将 config['neutralize_style'] 显式设为 [] 关闭风格剥离。"
        )

    return neutralize_cross_section(
        panel,
        industry_panel=industry_panel if use_industry else None,
        style_panel=style_panel,
        style_factors=style_factors,
    )
