"""生产写入往返、append upsert、daily_runner 当前行选择。"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from build import run, validate_output, write_production
from daily_runner import _select_current_result_row
from tests.fixtures import make_sample


def test_validate_output_rejects_nan_result_value() -> None:
    output = run(make_sample())
    bad = output.copy()
    bad.loc[0, "result_value"] = np.nan
    try:
        validate_output(bad)
    except ValueError as exc:
        assert "result_value" in str(exc)
    else:
        raise AssertionError("NaN result_value should raise ValueError")

    bad_inf = output.copy()
    bad_inf.loc[0, "result_value"] = np.inf
    try:
        validate_output(bad_inf)
    except ValueError as exc:
        assert "result_value" in str(exc)
    else:
        raise AssertionError("inf result_value should raise ValueError")


def test_validate_output_rejects_empty_required_strings() -> None:
    output = run(make_sample())
    for col in ["trade_date", "target_id", "source_data_date"]:
        bad = output.copy()
        bad.loc[0, col] = ""
        try:
            validate_output(bad)
        except ValueError as exc:
            assert col in str(exc)
        else:
            raise AssertionError(f"empty {col} should raise ValueError")


def test_write_production_round_trip(tmp_path: Path) -> None:
    output_path = tmp_path / "数据库.parquet"
    written = write_production(make_sample(), output_path, {"target_id": "round_trip", "data_version": "test-v1"})
    assert output_path.exists()
    reloaded = pd.read_parquet(output_path)
    assert list(reloaded.columns) == list(written.columns)
    assert (reloaded["build_id"] == "B10").all()
    assert reloaded.loc[0, "target_id"] == "round_trip"
    json.loads(reloaded.loc[0, "result_json"])


def test_write_production_append_upserts_by_primary_key(tmp_path: Path) -> None:
    output_path = tmp_path / "数据库.parquet"
    write_production(make_sample(), output_path, {"target_id": "factor_a", "data_version": "v1"}, mode="append")
    write_production(make_sample(), output_path, {"target_id": "factor_b", "data_version": "v1"}, mode="append")
    after_two = pd.read_parquet(output_path)
    assert len(after_two) == 2  # 两个不同 target_id 共存
    assert set(after_two["target_id"]) == {"factor_a", "factor_b"}

    # 同主键再写一次，应 upsert 覆盖（仍然 2 行）
    write_production(make_sample(), output_path, {"target_id": "factor_a", "data_version": "v2"}, mode="append")
    after_upsert = pd.read_parquet(output_path)
    assert len(after_upsert) == 2
    factor_a = after_upsert.loc[after_upsert["target_id"] == "factor_a"].iloc[0]
    assert factor_a["data_version"] == "v2"


def test_write_production_invalid_mode_raises(tmp_path: Path) -> None:
    try:
        write_production(make_sample(), tmp_path / "x.parquet", {"target_id": "t"}, mode="merge")
    except ValueError as exc:
        assert "mode" in str(exc)
    else:
        raise AssertionError("invalid mode should raise ValueError")


def test_run_accepts_parquet_path(tmp_path: Path) -> None:
    panel_path = tmp_path / "panel.parquet"
    make_sample().to_parquet(panel_path, index=False)
    output = run(panel_path)
    report = json.loads(output.loc[0, "result_json"])
    assert report["summary"]["sample_count"] > 0


def test_daily_runner_selects_current_target_from_appended_result() -> None:
    result = pd.DataFrame(
        [
            {
                "trade_date": "2026-01-02",
                "target_id": "other_factor",
                "result_type": "factor_evaluation_report",
                "update_time": "2026-01-02T16:00:00",
            },
            {
                "trade_date": "2026-01-01",
                "target_id": "current_factor",
                "result_type": "factor_evaluation_report",
                "update_time": "2026-01-05T16:00:00",
            },
        ]
    )
    row = _select_current_result_row(result, {"target_id": "current_factor"})
    assert row["target_id"] == "current_factor"
    assert row["trade_date"] == "2026-01-01"


def test_demo_panel_is_valid_b10_input() -> None:
    """演示脚本合成的面板必须是 B10 合法输入，且 RankIC 显著为正——这是给别人看
    "不联网也能本地跑通" 的招牌；如果哪天 _make_demo_panel 写歪了让 RankIC 变 0
    或负，演示就翻车了，所以锁住。"""
    from demo import _make_demo_panel

    panel = _make_demo_panel(n_days=20, n_assets=80, seed=12345)
    required = {"trade_date", "ts_code", "factor_value", "forward_return"}
    assert required.issubset(panel.columns)
    assert {"forward_return_1d", "forward_return_5d", "forward_return_20d"}.issubset(panel.columns)
    assert {"is_pool_all_a", "is_pool_hs300", "stock_pool_memberships"}.issubset(panel.columns)
    assert len(panel) == 20 * 80

    output = run(panel, {"target_id": "demo_test", "group_mode": "quintile"})
    report = json.loads(output.loc[0, "result_json"])
    assert report["summary"]["rank_ic"] > 0.05, "demo 面板 RankIC 应显著为正，否则演示无说服力"
    assert report["summary"]["sample_count"] == len(panel)
