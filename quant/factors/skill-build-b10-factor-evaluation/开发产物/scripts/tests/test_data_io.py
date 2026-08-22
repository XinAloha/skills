"""B10 输入校验 / 字段映射 / 主键 / 类型边界。"""

from __future__ import annotations

import pandas as pd

from build import run, validate_input
from tests.fixtures import make_sample


def test_validate_input_alias_columns() -> None:
    df = make_sample().rename(
        columns={
            "trade_date": "date",
            "ts_code": "asset",
            "factor_value": "factor",
            "forward_return": "return",
        }
    )
    normalized = validate_input(df)
    assert {"trade_date", "ts_code", "factor_value", "forward_return"}.issubset(normalized.columns)
    assert len(normalized) == len(df)


def test_empty_input_raises_clear_error() -> None:
    try:
        run([])
    except ValueError as exc:
        assert "不能为空" in str(exc)
    else:
        raise AssertionError("empty input should raise ValueError")


def test_missing_columns_raise_clear_error() -> None:
    try:
        run([{"trade_date": "2026-01-01", "ts_code": "000001.SZ"}])
    except ValueError as exc:
        assert "缺少必要字段" in str(exc)
    else:
        raise AssertionError("missing columns should raise ValueError")


def test_illegal_config_raises_clear_error() -> None:
    try:
        run(make_sample(), {"turnover_quantile": 1.5})
    except ValueError as exc:
        assert "turnover_quantile" in str(exc)
    else:
        raise AssertionError("illegal config should raise ValueError")

    try:
        run(make_sample(), {"annualization_factor": 0})
    except ValueError as exc:
        assert "annualization_factor" in str(exc)
    else:
        raise AssertionError("illegal annualization_factor should raise ValueError")

    try:
        run(make_sample(), {"group_mode": "invalid"})
    except ValueError as exc:
        assert "group_mode" in str(exc)
    else:
        raise AssertionError("illegal group_mode should raise ValueError")

    try:
        run(make_sample(), {"target_kind": "invalid"})
    except ValueError as exc:
        assert "target_kind" in str(exc)
    else:
        raise AssertionError("illegal target_kind should raise ValueError")

    try:
        run(make_sample(), {"group_mode": "decile", "group_count": 5})
    except ValueError as exc:
        assert "group_mode" in str(exc) and "group_count" in str(exc)
    else:
        raise AssertionError("conflicting group_mode and group_count should raise ValueError")


def test_invalid_numeric_type_raises_clear_error() -> None:
    bad = make_sample().copy()
    bad["factor_value"] = bad["factor_value"].astype(object)
    bad.loc[0, "factor_value"] = "not-a-number"
    try:
        run(bad)
    except ValueError as exc:
        assert "factor_value" in str(exc)
    else:
        raise AssertionError("invalid factor type should raise ValueError")


def test_invalid_horizon_return_type_raises_clear_error() -> None:
    bad = make_sample().copy()
    bad["forward_return_5d"] = bad["forward_return"].astype(object)
    bad.loc[0, "forward_return_5d"] = "not-a-number"
    try:
        run(bad, {"decay_horizons": [5]})
    except ValueError as exc:
        assert "forward_return_5d" in str(exc)
    else:
        raise AssertionError("invalid horizon return type should raise ValueError")


def test_blank_ts_code_raises_clear_error() -> None:
    bad = make_sample().copy()
    bad.loc[0, "ts_code"] = "   "
    try:
        run(bad)
    except ValueError as exc:
        assert "ts_code" in str(exc) and "空白" in str(exc)
    else:
        raise AssertionError("blank ts_code should raise ValueError")


def test_duplicate_primary_key_raises_clear_error() -> None:
    duplicated = pd.concat([make_sample(), make_sample().head(1)], ignore_index=True)
    try:
        run(duplicated)
    except ValueError as exc:
        assert "重复主键" in str(exc)
    else:
        raise AssertionError("duplicated trade_date + ts_code should raise ValueError")


def test_columns_config_strict_mapping() -> None:
    df = make_sample().rename(columns={"factor_value": "factor_raw", "forward_return": "ret_raw"})
    output = run(df, {"columns": {"factor_raw": "factor_value", "ret_raw": "forward_return"}})
    assert len(output) == 1

    # 多个原始字段映射到同一标准字段，应报错
    df_multi = make_sample().copy()
    df_multi["factor_alt"] = df_multi["factor_value"]
    try:
        run(df_multi, {"columns": {"factor_alt": "factor_value"}})
    except ValueError as exc:
        assert "columns" in str(exc) or "factor_value" in str(exc)
    else:
        raise AssertionError("conflicting target rename should raise ValueError")

    # 非字符串映射应报错
    try:
        run(make_sample(), {"columns": {"factor_value": 123}})
    except ValueError as exc:
        assert "columns" in str(exc)
    else:
        raise AssertionError("non-string columns mapping should raise ValueError")


def test_binary_success_rejects_out_of_range_labels() -> None:
    df = make_sample()
    df["forward_return"] = 1.5  # 越界
    try:
        run(df, {"target_kind": "binary_success"})
    except ValueError as exc:
        assert "binary_success" in str(exc) or "0/1" in str(exc) or "0-1" in str(exc)
    else:
        raise AssertionError("out-of-range binary_success label should raise ValueError")
