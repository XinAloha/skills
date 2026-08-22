"""V7 研究层输出与中性化 supplied panel 路径。"""

from __future__ import annotations

import json

import numpy as np

from build import render_report_html, run, validate_input
from tests.fixtures import make_research_sample, make_sample


def test_research_diagnostics_preserve_columns_and_render() -> None:
    df = make_research_sample()
    normalized = validate_input(df)
    assert "factor_component_same_day" in normalized.columns
    assert "position_state" in normalized.columns
    assert "ret_cc_t1_t2" in normalized.columns

    output = run(
        df,
        {
            "research_diagnostics": True,
            "return_targets": ["ret_oc_t1", "ret_oo_t1_t2", "ret_cc_t1_t2", "ret_vwap_t1_t2"],
            "group_mode": "quintile",
        },
    )
    report = json.loads(output.loc[0, "result_json"])
    diagnostics = report["research_diagnostics"]
    assert diagnostics["component_ic"]
    assert any(row["factor_col"] == "factor_component_same_day" for row in diagnostics["component_ic"])
    assert diagnostics["component_bins"]
    assert diagnostics["reverse_factor"]
    assert diagnostics["state_segments"]
    assert diagnostics["monthly_stability"]
    assert diagnostics["return_target_comparison"]["targets"]

    html = render_report_html(
        df,
        {
            "research_diagnostics": True,
            "return_targets": ["ret_oc_t1", "ret_oo_t1_t2", "ret_cc_t1_t2"],
            "group_mode": "quintile",
        },
    )
    assert "V7 Research Diagnostics" in html
    assert "Subfactor IC" in html
    assert "Return Target Comparison" in html


def test_neutralization_uses_supplied_exposure_panels_without_panda_data() -> None:
    df = make_sample()
    code_number = df["ts_code"].str.slice(0, 6).astype(int)
    industry_panel = df[["trade_date", "ts_code"]].drop_duplicates().copy()
    industry_panel["industry"] = np.where(
        industry_panel["ts_code"].str.slice(0, 6).astype(int).mod(2).eq(0),
        "industry_even",
        "industry_odd",
    )
    style_panel = df[["trade_date", "ts_code"]].copy()
    style_panel["log_market_cap"] = np.log(code_number + 1000)

    report = json.loads(
        run(
            df,
            {
                "neutralize": True,
                "industry_panel": industry_panel,
                "style_panel": style_panel,
                "neutralize_style": ["log_market_cap"],
            },
        ).loc[0, "result_json"]
    )
    assert report["summary"]["neutralized"] is True
    assert report["neutralization"]["enabled"] is True
    assert report["neutralization"]["daily_meta"]
    assert not any("error" in row for row in report["neutralization"]["daily_meta"])


def test_neutralization_without_supplied_panels_raises() -> None:
    """红线复检：B10 不联网。``neutralize=True`` 没有 industry/style panel 必须抛 ValueError。"""
    df = make_sample()
    try:
        run(df, {"neutralize": True})
    except ValueError as exc:
        msg = str(exc)
        assert "industry_panel" in msg or "style_panel" in msg
    else:
        raise AssertionError("neutralize=True without exposure panels should raise ValueError")
