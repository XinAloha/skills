"""run() 输出 schema、IC/分层语义、方向调整、binary_success、bootstrap、cost。"""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

from build import run
from tests.fixtures import make_pool_sample, make_sample


def test_run_outputs_build_schema_and_metrics() -> None:
    output = run(make_sample(), {"group_count": 5, "decay_horizons": [1, 3, 5]})
    required = {
        "trade_date",
        "build_id",
        "build_name",
        "target_id",
        "result_type",
        "result_value",
        "result_json",
        "source_data_date",
        "data_version",
        "update_time",
    }
    assert required.issubset(output.columns)
    assert len(output) == 1

    report = json.loads(output.loc[0, "result_json"])
    assert report["summary"]["sample_count"] == len(make_sample())
    assert "ic_analysis" in report
    assert "ic_time_analysis" in report
    assert "ic_distribution" in report
    assert "factor_distribution" in report
    assert "factor_rank_autocorrelation" in report
    assert "quality_checklist" in report
    assert "layer_backtest" in report
    assert "turnover_analysis" in report
    assert len(report["decay_curve"]) == 3
    assert report["summary"]["rank_ic"] > 0
    assert report["summary"]["group_count"] == 5
    assert "rank_ic_autocorr_lag1" in report["summary"]
    assert len(report["quality_checklist"]) >= 8


def test_run_accepts_file_path() -> None:
    path = Path(__file__).resolve().parents[2] / "references" / "sample_factor.csv"
    output = run(path)
    report = json.loads(output.loc[0, "result_json"])
    assert report["summary"]["sample_count"] > 0
    assert report["summary"]["date_count"] > 0
    assert report["summary"]["asset_count"] > 0


def test_negative_factor_direction_orients_metrics() -> None:
    df = make_sample()
    df["factor_value"] = -df["factor_value"]
    output = run(df, {"factor_direction": "negative", "group_count": 5})
    report = json.loads(output.loc[0, "result_json"])
    assert report["summary"]["raw_rank_ic"] < 0
    assert report["summary"]["rank_ic"] > 0
    assert report["summary"]["resolved_factor_direction"] == "negative"


def test_group_mode_selects_quintile_or_decile() -> None:
    quintile = json.loads(run(make_sample(), {"group_mode": "quintile"}).loc[0, "result_json"])
    decile = json.loads(run(make_sample(), {"group_mode": "decile"}).loc[0, "result_json"])
    chinese_decile = json.loads(run(make_sample(), {"group_mode": "十分组"}).loc[0, "result_json"])
    assert quintile["summary"]["group_count"] == 5
    assert quintile["summary"]["group_mode"] == "quintile"
    assert len(quintile["layer_backtest"]["group_mean_return"]) == 5
    assert decile["summary"]["group_count"] == 10
    assert decile["summary"]["group_mode"] == "decile"
    assert len(decile["layer_backtest"]["group_mean_return"]) == 10
    assert chinese_decile["summary"]["group_count"] == 10


def test_stock_pool_filter_selects_requested_pool() -> None:
    hs300 = json.loads(run(make_pool_sample(), {"stock_pool": "沪深300"}).loc[0, "result_json"])
    zz500 = json.loads(run(make_pool_sample(), {"stock_pool": "zz500"}).loc[0, "result_json"])
    all_a = json.loads(run(make_pool_sample(), {"stock_pool": "全A股"}).loc[0, "result_json"])
    assert hs300["summary"]["stock_pool"] == "hs300"
    assert hs300["summary"]["stock_pool_label"] == "沪深300"
    assert hs300["summary"]["asset_count"] == 10
    assert zz500["summary"]["stock_pool"] == "zz500"
    assert zz500["summary"]["asset_count"] == 10
    assert all_a["summary"]["stock_pool"] == "all_a"
    assert all_a["summary"]["asset_count"] == 40


def test_binary_success_target_reports_success_rates() -> None:
    df = make_pool_sample()
    ranks = df.groupby("trade_date")["factor_value"].rank(pct=True)
    df["forward_return"] = (ranks >= 0.75).astype(float)
    report = json.loads(
        run(
            df,
            {
                "target_kind": "binary_success",
                "group_mode": "decile",
                "decay_horizons": [1, 3],
            },
        ).loc[0, "result_json"]
    )
    assert report["summary"]["target_kind"] == "binary_success"
    assert report["summary"]["rank_ic"] > 0
    assert report["layer_backtest"]["group_mean_return"]["G10"] > report["layer_backtest"]["group_mean_return"]["G1"]
    assert 0 <= report["summary"]["long_short_cumulative_return"] <= 1


def test_decile_warns_when_cross_section_is_too_small() -> None:
    tiny_sample = make_sample().groupby("trade_date", group_keys=False).head(5)
    report = json.loads(run(tiny_sample, {"group_mode": "decile"}).loc[0, "result_json"])
    assert report["summary"]["configured_group_count"] == 10
    assert report["summary"]["group_count"] < 10
    assert any("实际分为" in warning for warning in report["quality_warnings"])


def test_constant_factor_does_not_crash_and_warns() -> None:
    df = make_sample()
    df["factor_value"] = 0.5
    output = run(df)
    report = json.loads(output.loc[0, "result_json"])
    # IC 全部为 NaN 后被过滤，rank_ic 收敛为 0.0，且 quality_warnings 应包含至少一条提示
    assert report["summary"]["rank_ic"] is not None
    assert any("没有可计算 IC" in warning or "横截面" in warning for warning in report["quality_warnings"])


def test_single_trade_date_degrades_gracefully() -> None:
    df = make_sample()
    df = df.loc[df["trade_date"] == df["trade_date"].iloc[0]].copy()
    output = run(df)
    report = json.loads(output.loc[0, "result_json"])
    assert report["summary"]["date_count"] == 1
    # 单日下 IC 自相关、ICIR 等无法稳定计算，但 run 不能崩溃
    assert any("交易日" in warning or "横截面" in warning or "稳定" in warning for warning in report["quality_warnings"])


def test_decay_horizons_larger_than_days_safe() -> None:
    # 只有 24 个交易日，但请求 60 期衰减
    output = run(make_sample(), {"decay_horizons": [1, 60, 120]})
    report = json.loads(output.loc[0, "result_json"])
    horizons = [row["horizon"] for row in report["decay_curve"]]
    assert horizons == [1, 60, 120]
    # 超出范围的 horizon 至少应有 sample_days，sample_days 可能为 0 但不应抛错
    assert all("sample_days" in row for row in report["decay_curve"])


def test_transaction_cost_sweep_is_explicit_opt_in() -> None:
    default_report = json.loads(run(make_sample(), {"cost_grid_bps": []}).loc[0, "result_json"])
    assert default_report["transaction_cost"]["cost_grid_bps"] == []
    assert default_report["transaction_cost"]["sweep"] == []

    cost_report = json.loads(run(make_sample(), {"cost_grid_bps": [1, 5]}).loc[0, "result_json"])
    sweep = cost_report["transaction_cost"]["sweep"]
    assert [row["cost_bps"] for row in sweep] == [1.0, 5.0]
    assert all("net_long_short_ir" in row for row in sweep)


def test_bootstrap_rank_ic_baseline_is_reported_when_enabled() -> None:
    report = json.loads(run(make_sample(), {"bootstrap_n": 20, "bootstrap_seed": 123}).loc[0, "result_json"])
    baseline = report["bootstrap_baseline"]
    assert baseline["n_boot"] == 20
    assert baseline["n_days"] > 0
    assert 0.0 <= baseline["p_two_sided"] <= 1.0
    assert abs(baseline["observed"] - report["summary"]["rank_ic"]) < 1e-6


def test_monotonicity_direction_reflects_resolved_factor_direction() -> None:
    pos = json.loads(run(make_sample(), {"factor_direction": "positive"}).loc[0, "result_json"])
    assert pos["layer_backtest"]["monotonicity"]["direction"] == "increasing"

    df = make_sample()
    df["factor_value"] = -df["factor_value"]
    neg = json.loads(run(df, {"factor_direction": "negative"}).loc[0, "result_json"])
    assert neg["layer_backtest"]["monotonicity"]["direction"] == "decreasing"

    auto = json.loads(run(df, {"factor_direction": "auto"}).loc[0, "result_json"])
    # auto 翻转：原 raw RankIC < 0，方向解析为 negative，monotonicity.direction = decreasing
    assert auto["summary"]["resolved_factor_direction"] == "negative"
    assert auto["layer_backtest"]["monotonicity"]["direction"] == "decreasing"


def test_package_import_entrypoint() -> None:
    root = Path(__file__).resolve().parents[2]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    module = importlib.import_module("scripts.build")
    output = module.run(make_sample(), {"annualization_factor": 52, "decay_horizons": [1, 2]})
    report = json.loads(output.loc[0, "result_json"])
    assert report["summary"]["annualization_factor"] == 52.0
    assert len(report["decay_curve"]) == 2


def test_make_report_equivalent_to_split_path() -> None:
    """make_report 直接调用 vs compute_panel_base + apply_layer 结果必须按位等价。"""
    import metrics as M
    from data_io import validate_input as data_io_validate_input
    from utils import json_safe

    df = make_pool_sample()
    panel = data_io_validate_input(df, M.validate_config({}))

    config = M.validate_config({"group_mode": "decile", "stock_pool": "all_a"})
    direct = json_safe(M.make_report(panel, config))
    base = M.compute_panel_base(panel, config)
    via_split = json_safe(M.apply_layer(base, config))
    assert direct == via_split, "拆分前后 make_report 输出必须按位等价"

    # 用同一 base 切到 quintile，apply_layer 必须重算 layer/research/checklist；
    # IC/turnover/decay 等 base 缓存字段必须与原 quintile 直跑等价。
    quintile_cfg = M.validate_config({"group_mode": "quintile", "stock_pool": "all_a"})
    quintile_via_split = json_safe(M.apply_layer(base, quintile_cfg))
    quintile_direct = json_safe(M.make_report(panel, quintile_cfg))
    for key in (
        "ic_analysis",
        "raw_ic_analysis",
        "ic_time_analysis",
        "ic_distribution",
        "factor_distribution",
        "factor_rank_autocorrelation",
        "turnover_analysis",
        "decay_curve",
    ):
        assert quintile_via_split[key] == quintile_direct[key], (
            f"切换 group_count 后 {key} 必须由 base 缓存复用，结果应与直跑一致"
        )
    # 而 layer / quality_checklist 必须真的随 group_count 改变。
    assert quintile_via_split["layer_backtest"]["group_count"] == 5
    assert quintile_via_split["summary"]["group_count"] == 5
