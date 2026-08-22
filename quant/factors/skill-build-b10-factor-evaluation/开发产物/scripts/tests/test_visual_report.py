"""HTML 渲染、图表占位、性能拆分（make_group_reports 复用 base）。"""

from __future__ import annotations

from build import render_report_html
from tests.fixtures import make_pool_sample


def test_render_report_outputs_html() -> None:
    html = render_report_html(
        make_pool_sample(),
        {"target_id": "sample_factor", "group_count": 5, "decay_horizons": [1, 3, 5]},
    )
    assert "IC测试与因子评估体系" in html
    assert "核心图表" in html
    assert "优质因子特征达标表" in html
    assert "Cumulative IC" in html
    assert "Factor Distribution Diagnostics" in html
    assert "成功率" not in html
    assert 'id="group-mode-select"' in html
    assert '<option value="quintile" selected>五分组</option>' in html
    assert '<option value="decile">十分组</option>' in html
    assert 'id="stock-pool-select"' in html
    assert '<option value="hs300">沪深300</option>' in html
    assert html.count('class="group-report"') == 10
    assert html.count("<svg") >= 60


def test_make_group_reports_reuses_panel_base() -> None:
    """visual_report.make_group_reports 必须每个 stock_pool 只算一次 base。

    通过 monkeypatch 计数 compute_panel_base 调用次数：
    - n_pools 个股票池 × 2 个 group_mode = 2n 个 (pool, mode) 组合
    - 拆分前 make_report 被调 2n 次
    - 拆分后 base 应只被调 n 次，apply_layer 调 2n 次
    """
    import metrics as M
    import visual_report as VR
    from visual import document as VR_DOC
    from data_io import validate_input as data_io_validate_input

    df = make_pool_sample()

    base_calls = {"n": 0}
    apply_calls = {"n": 0}
    real_base = M.compute_panel_base
    real_apply = M.apply_layer

    def counting_base(panel, config):
        base_calls["n"] += 1
        return real_base(panel, config)

    def counting_apply(base, config):
        apply_calls["n"] += 1
        return real_apply(base, config)

    M.compute_panel_base = counting_base
    M.apply_layer = counting_apply
    VR.compute_panel_base = counting_base
    VR.apply_layer = counting_apply
    # visual.document 是 make_group_reports 的实际调用点（v1.4 拆分后），单独 patch
    # 才会被命中。同时 patch VR/M 是为了兼容历史 monkeypatch 习惯。
    VR_DOC.compute_panel_base = counting_base
    VR_DOC.apply_layer = counting_apply
    try:
        config = M.validate_config(
            {"group_mode": "decile", "enable_stock_pool_selector": True, "enable_group_selector": True}
        )
        panel = data_io_validate_input(df, config)
        reports = VR.make_group_reports(panel, config)
    finally:
        M.compute_panel_base = real_base
        M.apply_layer = real_apply
        VR.compute_panel_base = real_base
        VR.apply_layer = real_apply
        VR_DOC.compute_panel_base = real_base
        VR_DOC.apply_layer = real_apply

    pools = VR.available_stock_pools(panel)
    n_pools = len(pools)
    assert base_calls["n"] == n_pools, (
        f"每个 stock_pool 应只计算一次 panel base，期望 {n_pools} 次，实际 {base_calls['n']} 次"
    )
    assert apply_calls["n"] == n_pools * 2, (
        f"每个 (pool, mode) 一次 apply_layer，期望 {n_pools*2} 次，实际 {apply_calls['n']} 次"
    )
    assert len(reports) == n_pools * 2
