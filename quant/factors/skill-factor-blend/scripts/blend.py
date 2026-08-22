#!/usr/bin/env python
"""
多因子信号层合并 — 去冗余 + 加权合成
用法: python scripts/blend.py [--factor-dir data/factors] [--weight equal|icir|score]
     若未指定 --weight，交互式询问用户选择权重方案。
"""
import sys
from pathlib import Path
import argparse
import json
import pickle
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

_SCRIPT_DIR = Path(__file__).resolve().parent
_SKILLS_DIR = _SCRIPT_DIR.parent.parent
_PANDADATA_SCRIPTS = _SKILLS_DIR / "skill-pandadata-api" / "scripts"
if _PANDADATA_SCRIPTS.is_dir():
    sys.path.insert(0, str(_PANDADATA_SCRIPTS))
COMBINE_STATE_FILENAME = "combine_state.pkl"
COMBINE_REPORT_FILENAME = "combine_report.json"

WEIGHT_SCHEMES = {
    "equal": "等权 — 所有因子权重相同，适合因子质量接近的场景",
    "icir": "ICIR 加权 — 按信息比率 (IC_mean/IC_std) 分配权重，奖励稳定因子",
    "score": "Score 加权 — 按综合评分分配权重（需 factor-evaluate 报告），适合质量差异大的场景",
}


def daily_rank_ic(signal: pd.Series, fwd_ret: pd.Series) -> pd.Series:
    df = pd.DataFrame({"signal": signal, "fwd_ret": fwd_ret})
    results = {}
    for d, grp in df.groupby(level="date"):
        grp = grp.dropna()
        if len(grp) < 10:
            results[d] = np.nan
            continue
        ic, _ = spearmanr(grp["signal"], grp["fwd_ret"])
        results[d] = ic
    return pd.Series(results, name="rank_ic")


def daily_turnover(signal: pd.Series) -> float:
    df = signal.to_frame("signal")
    to_vals = []
    dates_sorted = sorted(df.index.get_level_values("date").unique())
    for i, d in enumerate(dates_sorted[1:], 1):
        prev_d = dates_sorted[i - 1]
        s_today = df.loc[d]["signal"]
        s_prev = df.loc[prev_d]["signal"]
        common = s_today.index.intersection(s_prev.index)
        if len(common) < 10:
            continue
        today_rank = s_today.loc[common].rank(pct=True)
        prev_rank = s_prev.loc[common].rank(pct=True)
        to_vals.append((today_rank - prev_rank).abs().mean())
    return np.mean(to_vals) if to_vals else np.nan


def factor_correlation(factors: dict) -> pd.DataFrame:
    """计算因子间截面 Rank 相关矩阵"""
    names = list(factors.keys())
    corr = pd.DataFrame(np.eye(len(names)), index=names, columns=names)
    for i, a in enumerate(names):
        for j, b in enumerate(names):
            if i >= j:
                continue
            common = factors[a].dropna().index.intersection(factors[b].dropna().index)
            if len(common) < 30:
                corr.loc[a, b] = corr.loc[b, a] = np.nan
                continue
            corr.loc[a, b] = corr.loc[b, a] = factors[a].loc[common].corr(factors[b].loc[common], method="spearman")
    return corr


def remove_redundant(factors: dict, icirs: dict, corr_threshold: float = 0.7) -> dict:
    """去冗余：同簇因子（corr > threshold）只保留 ICIR 最高者"""
    corr = factor_correlation(factors)
    survivors = dict(factors)
    removed = []

    for i, a in enumerate(corr.columns):
        for b in corr.columns[i + 1:]:
            if a not in survivors or b not in survivors:
                continue
            if abs(corr.loc[a, b]) > corr_threshold:
                # 保留 ICIR 更高者
                if icirs.get(a, 0) >= icirs.get(b, 0):
                    removed.append(b)
                    del survivors[b]
                else:
                    removed.append(a)
                    del survivors[a]
                    break

    if removed:
        print(f"  去冗余: 移除 {removed} (corr > {corr_threshold})")
    return survivors


def compute_fast_icir(signal: pd.Series, fwd_ret: pd.Series) -> float:
    """快速计算 ICIR（抽样计算，避免全量 IC）"""
    ic = daily_rank_ic(signal, fwd_ret).dropna()
    if len(ic) < 20 or ic.std() == 0:
        return 0.0
    return ic.mean() / ic.std()


def make_composite(factors: dict, weights: dict) -> pd.Series:
    """加权合成：每个因子截面 z-score 后取加权均值"""
    all_dates = sorted(set().union(*[set(s.index.get_level_values("date")) for s in factors.values()]))
    daily_chunks = []
    total_w = sum(weights.values())

    for d in all_dates:
        day_vals = []
        for name, signal in factors.items():
            w = weights.get(name, 0) / total_w
            try:
                day_s = signal.loc[d].dropna()
                day_s = (day_s - day_s.mean()) / day_s.std()
                if len(day_s) > 10:
                    day_vals.append(day_s * w)
            except (KeyError, AttributeError):
                continue
        if not day_vals:
            continue
        composite = pd.concat(day_vals, axis=1).sum(axis=1)
        composite.index = pd.MultiIndex.from_tuples(
            [(d, sym) for sym in composite.index], names=["date", "symbol"])
        # 最终 z-score
        composite = (composite - composite.mean()) / composite.std()
        daily_chunks.append(composite)

    result = pd.concat(daily_chunks)
    result.name = "factor_value"
    return result


def interactive_weight_selection(scheme_arg: str = None) -> str:
    """交互式询问用户选择权重方案，或从 CLI 参数读取"""
    if scheme_arg and scheme_arg in WEIGHT_SCHEMES:
        return scheme_arg

    print("\n" + "=" * 60)
    print("⚖️  权重方案选择")
    print("=" * 60)
    for key, desc in WEIGHT_SCHEMES.items():
        print(f"  [{key}]  {desc}")
    print()

    # CLI 交互
    while True:
        choice = input("请选择权重方案 [equal/icir/score] (默认 equal): ").strip().lower()
        if not choice:
            return "equal"
        if choice in WEIGHT_SCHEMES:
            return choice
        print(f"  ⚠️  无效选择 '{choice}'，请输入 equal / icir / score")


def main():
    parser = argparse.ArgumentParser(description="多因子信号层合并")
    parser.add_argument("--factor-dir", default="data/factors",
                        help="因子输入目录（相对于工作目录或绝对路径）")
    parser.add_argument("--output-dir", default="data",
                        help="合成因子输出目录")
    parser.add_argument("--weight", choices=["equal", "icir", "score"],
                        help="权重方案（不指定则交互式询问）")
    parser.add_argument("--corr-threshold", type=float, default=0.7,
                        help="去冗余相关性阈值")
    parser.add_argument("--indicator", default="000300",
                        help="Pandadata 股票池指数代码 (默认 000300=沪深300)")
    parser.add_argument("--start-date", default="20201201",
                        help="Pandadata 起始日期 YYYYMMDD")
    parser.add_argument("--end-date", default="20250131",
                        help="Pandadata 结束日期 YYYYMMDD")
    args = parser.parse_args()

    factor_dir = Path(args.factor_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. 加载因子
    factor_files = sorted(factor_dir.glob("F*.parquet"))
    if not factor_files:
        print(f"❌ 未找到因子文件: {factor_dir}")
        return

    print(f"加载 {len(factor_files)} 个因子: {factor_dir}")
    factors = {}
    for fp in factor_files:
        df = pd.read_parquet(fp)
        df["date"] = pd.to_datetime(df["date"])
        factors[fp.stem] = df.set_index(["date", "symbol"])["factor_value"]
        print(f"  {fp.stem}: {len(factors[fp.stem])} 行")

    # 2. 快速 ICIR 估计（用 forward_ret_5d）
    print("\n计算因子 ICIR...")
    try:
        from pandadata_runtime import init_pandadata
    except ImportError:
        print('❌ 无法导入 pandadata_runtime。请确保 skill-pandadata-api 已安装。')
        sys.exit(1)
    pd_api = init_pandadata()
    raw = pd_api.get_stock_daily(start_date=args.start_date, end_date=args.end_date, fields=[], indicator=args.indicator, st=False)
    raw["date"] = pd.to_datetime(raw["date"], format="%Y%m%d")
    raw.columns = [c.lower() for c in raw.columns]
    raw = raw.sort_values(["symbol", "date"])
    raw["forward_ret_5d"] = raw.groupby("symbol")["close"].shift(-5) / raw["close"] - 1
    fwd_ret_5d = raw.set_index(["date", "symbol"])["forward_ret_5d"]

    icirs = {}
    for name, signal in factors.items():
        icirs[name] = compute_fast_icir(signal, fwd_ret_5d)
    for name, icir in sorted(icirs.items(), key=lambda x: -x[1]):
        print(f"  {name}: ICIR={icir:+.3f}")

    # 3. 去冗余
    print(f"\n去冗余（corr > {args.corr_threshold}）...")
    factors = remove_redundant(factors, icirs, args.corr_threshold)
    print(f"  保留 {len(factors)} 个因子: {list(factors.keys())}")

    # 4. ⚖️ 交互式权重选择
    scheme = interactive_weight_selection(args.weight)
    print(f"\n✅ 选择: {scheme} — {WEIGHT_SCHEMES[scheme]}")

    # 5. 计算权重
    if scheme == "equal":
        weights = {name: 1.0 for name in factors}
    elif scheme == "icir":
        raw_icir = {name: max(0.01, icirs.get(name, 0)) for name in factors}
        total = sum(raw_icir.values())
        weights = {name: v / total for name, v in raw_icir.items()}
    elif scheme == "score":
        # Score = ICIR * sqrt(coverage) * (1 / (1 + turnover)) 简易评分
        scores = {}
        for name, signal in factors.items():
            icir = max(0.01, icirs.get(name, 0))
            coverage = signal.notna().mean()
            to = daily_turnover(signal)
            scores[name] = icir * np.sqrt(coverage) / (1 + max(0.01, to))
        total = sum(scores.values())
        weights = {name: v / total for name, v in scores.items()}

    print("\n因子权重:")
    for name, w in sorted(weights.items(), key=lambda x: -x[1]):
        print(f"  {name}: {w:.4f}")

    # 6. 合成
    print("\n合成复合因子...")
    composite = make_composite(factors, weights)
    print(f"  composite: {len(composite)} 个样本")

    # 7. 保存
    out_df = composite.reset_index()
    out_df.columns = ["date", "symbol", "factor_value"]
    out_path = output_dir / f"composite_{scheme}-weighted.parquet"
    out_df.to_parquet(out_path, index=False)
    print(f"  保存: {out_path}")

    # 保存中间态
    state = {
        "scheme": scheme,
        "weights": weights,
        "icirs": icirs,
        "factor_names": list(factors.keys()),
        "n_factors_original": len(factor_files),
        "n_factors_after_dedup": len(factors),
    }
    st_path = output_dir / COMBINE_STATE_FILENAME
    rp_path = output_dir / COMBINE_REPORT_FILENAME
    pickle.dump(state, st_path.open("wb"))
    json.dump(state, rp_path.open("w"), indent=2, ensure_ascii=False, default=str)

    # 8. 快速评价
    print(f"\n复合因子快速评价:")
    ic = daily_rank_ic(composite, fwd_ret_5d).dropna()
    print(f"  Rank IC(5d): {ic.mean():+.5f}, ICIR: {ic.mean()/ic.std():+.3f}, Sharpe: {ic.mean()/ic.std()*np.sqrt(252):+.2f}")
    print(f"  Coverage: {composite.notna().mean():.1%}")
    to = daily_turnover(composite)
    print(f"  Turnover: {to:.4f}")

    print(f"\n✅ 合并完成")
    print(f"   复合因子: {out_path}")
    print(f"   中间态: {st_path}")
    print(f"   报告: {rp_path}")


if __name__ == "__main__":
    main()
