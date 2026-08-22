"""B10 HTML 报告组装层。

负责拼整篇 HTML、做股票池/分组下拉切换、把多 (pool, group_mode) 共享 panel base
后统一调用 ``apply_layer`` 出报告。

层次定位
- 上：``build.py`` / ``daily_runner.py`` 调 ``write_report`` / ``render_report_html``。
- 下：调用 ``sections`` 拿章节 HTML、调用 ``metrics.compute_panel_base`` /
  ``metrics.apply_layer`` 拿评估结果。
"""

from __future__ import annotations

from datetime import datetime
from html import escape
from pathlib import Path
from typing import Any

import pandas as pd

try:
    from ..constants import BUILD_NAME, STOCK_POOL_LABELS
    from ..data_io import validate_input
    from ..metrics import apply_layer, compute_panel_base, make_report, validate_config
    from ..utils import json_safe
    from .sections import render_report_sections
except ImportError:
    from constants import BUILD_NAME, STOCK_POOL_LABELS
    from data_io import validate_input
    from metrics import apply_layer, compute_panel_base, make_report, validate_config
    from utils import json_safe
    from visual.sections import render_report_sections


def group_mode_label(mode: str) -> str:
    return "十分组" if mode == "decile" else "五分组"


def config_for_group_mode(config: dict[str, Any], group_mode: str) -> dict[str, Any]:
    group_config = {k: v for k, v in config.items() if k not in {"group_count", "group_mode"}}
    group_config["group_mode"] = group_mode
    return validate_config(group_config)


def available_stock_pools(panel: pd.DataFrame) -> list[str]:
    pools = ["all_a"]
    for pool, label in STOCK_POOL_LABELS.items():
        if pool == "all_a":
            continue
        flag_col = f"is_pool_{pool}"
        has_pool = False
        if flag_col in panel.columns:
            has_pool = bool(panel[flag_col].astype(bool).any())
        elif "stock_pool_memberships" in panel.columns:
            values = panel["stock_pool_memberships"].fillna("").astype(str)
            has_pool = bool(
                values.str.contains(label, regex=False).any()
                or values.str.contains(pool, regex=False).any()
            )
        if has_pool:
            pools.append(pool)
    return pools


def render_group_selector(
    selected_mode: str,
    selected_stock_pool: str = "all_a",
    stock_pool_options: list[str] | None = None,
) -> str:
    options = [
        ("quintile", "五分组"),
        ("decile", "十分组"),
    ]
    option_html = "".join(
        f'<option value="{value}"{" selected" if value == selected_mode else ""}>{label}</option>'
        for value, label in options
    )
    pool_options = stock_pool_options or ["all_a"]
    pool_html = "".join(
        f'<option value="{pool}"{" selected" if pool == selected_stock_pool else ""}>{STOCK_POOL_LABELS[pool]}</option>'
        for pool in pool_options
    )
    pool_control = ""
    if pool_options:
        pool_control = (
            f'<label for="stock-pool-select">股票池</label>'
            f'<select id="stock-pool-select" aria-label="股票池">{pool_html}</select>'
        )
    return (
        '<div class="report-toolbar">'
        '<label for="group-mode-select">分组选项</label>'
        f'<select id="group-mode-select" aria-label="分组选项">{option_html}</select>'
        f'{pool_control}</div>'
    )


def render_html_report(
    report: dict[str, Any],
    config: dict[str, Any],
    group_reports: dict[str, dict[str, Any]] | None = None,
) -> str:
    summary = report["summary"]
    is_binary = str(summary.get("target_kind", config.get("target_kind", "return"))) == "binary_success"
    target_id = str(config.get("target_id", "factor_evaluation_report"))
    generated_at = str(config.get("update_time", datetime.now().isoformat(timespec="seconds")))
    selected_mode = str(summary.get("group_mode", config.get("group_mode", "quintile")))
    selected_stock_pool = str(summary.get("stock_pool", config.get("stock_pool", "all_a")))
    if group_reports:
        keys = list(group_reports.keys())
        parsed_keys = [(key[0], key[1]) if isinstance(key, tuple) else ("all_a", str(key)) for key in keys]
        pool_options: list[str] = []
        for pool, _ in parsed_keys:
            if pool not in pool_options:
                pool_options.append(pool)
        selector_html = render_group_selector(selected_mode, selected_stock_pool, pool_options)
        sections = []
        for key, group_report in group_reports.items():
            pool, mode = (key[0], key[1]) if isinstance(key, tuple) else ("all_a", str(key))
            hidden = mode != selected_mode or pool != selected_stock_pool
            title = f"{STOCK_POOL_LABELS.get(pool, pool)} / {group_mode_label(mode)}"
            sections.append(
                f'<section class="group-report" data-group-mode="{mode}" data-stock-pool="{pool}"'
                f'{" hidden" if hidden else ""}>'
                f'<div class="mode-title">{escape(title)}</div>{render_report_sections(group_report)}</section>'
            )
        content_html = "".join(sections)
        script_html = """<script>
(function () {
  var groupControl = document.getElementById("group-mode-select");
  var poolControl = document.getElementById("stock-pool-select");
  var reports = document.querySelectorAll(".group-report");
  function applySelectors() {
    reports.forEach(function (report) {
      var groupOk = !groupControl || report.getAttribute("data-group-mode") === groupControl.value;
      var poolOk = !poolControl || report.getAttribute("data-stock-pool") === poolControl.value;
      report.hidden = !(groupOk && poolOk);
    });
  }
  if (groupControl) {
    groupControl.addEventListener("change", applySelectors);
  }
  if (poolControl) {
    poolControl.addEventListener("change", applySelectors);
  }
  applySelectors();
})();
</script>"""
    else:
        selector_html = ""
        content_html = render_report_sections(report)
        script_html = ""

    return f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(BUILD_NAME)} - {escape(target_id)}</title>
<style>
:root{{--ink:#17202a;--muted:#5f6b7a;--paper:#fbfcfd;--panel:#fff;--line:#d8dee8;--blue:#1f4e79}}
*{{box-sizing:border-box}} body{{margin:0;color:var(--ink);background:var(--paper);font-family:"Inter","Segoe UI","Microsoft YaHei",Arial,sans-serif;line-height:1.55}}
main{{width:min(1180px,calc(100vw - 48px));margin:0 auto;padding:34px 0 54px}} header{{border-bottom:1px solid var(--line);padding-bottom:22px;margin-bottom:26px}}
h1{{margin:0 0 8px;font-size:31px;font-weight:760;letter-spacing:0}} h2{{margin:30px 0 14px;font-size:19px;letter-spacing:0}}
.subtitle,.meta,.metric-label,.metric-note,figcaption{{color:var(--muted)}} .meta{{display:flex;gap:18px;flex-wrap:wrap;font-size:13px;margin-top:14px}}
.report-toolbar{{display:flex;align-items:center;gap:10px;margin-top:18px}} .report-toolbar label{{font-size:13px;color:var(--muted)}} .report-toolbar select{{height:34px;border:1px solid var(--line);border-radius:6px;background:#fff;color:var(--ink);padding:0 34px 0 12px;font-size:13px}}
.mode-title{{font-size:14px;font-weight:720;color:var(--blue);margin:4px 0 12px}} .group-report[hidden]{{display:none}}
.metrics{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin:22px 0 8px}} .metric-card,figure,table{{background:var(--panel);border:1px solid var(--line);border-radius:8px}}
.metric-card{{padding:13px 14px}} .metric-label,.metric-note,figcaption{{font-size:12px}} .metric-value{{font-size:23px;font-weight:760;font-variant-numeric:tabular-nums}}
.figure-grid,.tables{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}} figure{{margin:0;padding:14px}} .chart{{display:block;width:100%;height:auto}}
.chart-title{{font-size:16px;font-weight:720;fill:var(--ink)}} .axis,.zero{{stroke:#8a96a8;stroke-width:1}} .zero{{stroke-dasharray:4 4}} .grid{{stroke:#e8edf3;stroke-width:1}}
.axis-label,.legend{{fill:#647184;font-size:11px;font-variant-numeric:tabular-nums}} table{{width:100%;border-collapse:collapse;overflow:hidden;font-size:13px}}
th,td{{padding:10px 12px;border-bottom:1px solid var(--line);text-align:right;font-variant-numeric:tabular-nums}} th:first-child,td:first-child{{text-align:left}} th{{color:var(--muted);font-weight:650;background:#f4f7fa}}
.method{{color:var(--muted);background:#f4f7fa;border-left:3px solid var(--blue);padding:12px 14px;border-radius:6px;font-size:13px}} .warnings{{margin:0 0 8px;padding:12px 16px 12px 30px;background:#fff7ed;border:1px solid #fed7aa;border-radius:8px;color:#8a4b12;font-size:13px}}
@media(max-width:900px){{main{{width:min(100vw - 28px,1180px)}}.metrics,.figure-grid,.tables{{grid-template-columns:1fr}}}}
</style></head><body><main>
<header><h1>{escape(BUILD_NAME)}</h1><div class="subtitle">{'因子值与次日封板成功标签输入生成的打板接力评估报告' if is_binary else '因子值与未来收益输入生成的科研级因子评估报告'}</div>
<div class="meta"><span>评估对象：{escape(target_id)}</span><span>目标口径：{escape('次日封板成功率' if is_binary else '未来收益')}</span><span>股票池：{escape(str(summary.get("stock_pool_label", "全A股")))}</span><span>样本区间：{escape(str(summary["start_date"]))} 至 {escape(str(summary["end_date"]))}</span><span>样本数：{int(summary["sample_count"])}</span><span>标的数：{int(summary["asset_count"])}</span><span>生成时间：{escape(generated_at)}</span></div>{selector_html}</header>
{content_html}{script_html}</main></body></html>"""


def make_group_reports(panel: pd.DataFrame, config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """五分组/十分组 × 各股票池一次性出报告。

    性能拆分（v1.2.0）：每个 stock_pool 调一次 compute_panel_base 共享
    daily IC / time / distribution / factor_dist / rank_autocorr / turnover /
    decay 等 group_count 无关的预计算，再对 quintile / decile 分别
    apply_layer。原先每个 (pool, mode) 都重头跑一次完整 make_report，
    pool 数 × 2 mode 次重复计算降到 pool 数次 base + pool 数 × 2 次
    layer/research/checklist。
    """
    group_modes = ["quintile", "decile"]
    pool_options = (
        available_stock_pools(panel)
        if bool(config.get("enable_stock_pool_selector", True))
        else [config["stock_pool"]]
    )
    reports: dict[str, dict[str, Any]] = {}
    for pool in pool_options:
        # 任何一个 mode 的 validate_config 都能验证出 pool/turnover/horizons 是否非法；
        # base 失败（例如该股票池在该区间无样本）整 pool 跳过。
        pool_config_template = {**config, "stock_pool": pool}
        try:
            base_config = config_for_group_mode(pool_config_template, group_modes[0])
            base = compute_panel_base(panel, base_config)
        except ValueError:
            continue
        for mode in group_modes:
            try:
                report_config = config_for_group_mode(pool_config_template, mode)
            except ValueError:
                continue
            try:
                reports[(pool, mode)] = json_safe(apply_layer(base, report_config))
            except ValueError:
                continue
    return reports


def render_report_html(input_data: Any, config: dict | None = None) -> str:
    config = validate_config(config or {})
    config = {**config, "update_time": str(config.get("update_time", datetime.now().isoformat(timespec="seconds")))}
    panel = validate_input(input_data, config)
    if config["group_mode"] in {"quintile", "decile"} and bool(config.get("enable_group_selector", True)):
        group_reports = make_group_reports(panel, config)
        selected_key = (config["stock_pool"], config["group_mode"])
        selected_report = group_reports.get(selected_key) or next(iter(group_reports.values()))
        return render_html_report(selected_report, config, group_reports)
    return render_html_report(json_safe(make_report(panel, config)), config)


def write_report(input_data: Any, output_path: str | Path | None = None, config: dict | None = None) -> Path:
    config = validate_config(config or {})
    config = {**config, "update_time": str(config.get("update_time", datetime.now().isoformat(timespec="seconds")))}
    panel = validate_input(input_data, config)
    report = make_report(panel, config)
    if output_path is None:
        safe_target = str(config.get("target_id", "factor_evaluation_report")).replace("/", "_").replace("\\", "_")
        output_path = Path("reports") / f"{safe_target}_{report['summary']['end_date']}.html"
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if config["group_mode"] in {"quintile", "decile"} and bool(config.get("enable_group_selector", True)):
        group_reports = make_group_reports(panel, config)
        selected_key = (config["stock_pool"], config["group_mode"])
        selected_report = group_reports.get(selected_key, json_safe(report))
        html = render_html_report(selected_report, config, group_reports)
    else:
        html = render_html_report(json_safe(report), config)
    output_path.write_text(html, encoding="utf-8")
    return output_path
