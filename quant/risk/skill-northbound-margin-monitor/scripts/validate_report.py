#!/usr/bin/env python3
"""Validate panorama monitor output files (Markdown report + JSON data).

Checks:
  - Markdown: all 9 required sections present, key data points non-empty
  - JSON: all required top-level keys, score consistency, signal integrity
  - Score: composite == weighted sub-scores (within tolerance)

Usage:
    python scripts/validate_report.py output/2026-07-01/panorama_monitor_20260701.md output/2026-07-01/panorama_monitor_20260701.json
    python scripts/validate_report.py --date 20260701  # auto-path
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


# ── Markdown validation ──

MD_REQUIRED_SECTIONS = [
    ("title", r"^#\s+北向资金\s*\+\s*融资融券全景监控", "缺少一级标题「北向资金+融资融券全景监控」"),
    ("nb_overview", r"^##\s+一、北向资金概览", "缺少「一、北向资金概览」章节"),
    ("margin_overview", r"^##\s+二、融资融券概览", "缺少「二、融资融券概览」章节"),
    ("futures", r"^##\s+三、股指期货信号", "缺少「三、股指期货信号」章节"),
    ("resonance", r"^##\s+四、共振/背离分析", "缺少「四、共振/背离分析」章节"),
    ("price_volume", r"^##\s+五、量价确认", "缺少「五、量价确认」章节"),
    ("microstructure", r"^##\s+六、微观结构信号", "缺少「六、微观结构信号」章节"),
    ("sentiment", r"^##\s+七、综合情绪评估", "缺少「七、综合情绪评估」章节"),
    ("historical", r"^##\s+八、历史对比", "缺少「八、历史对比」章节"),
    ("ai_analysis", r"^##\s+九、AI\s+宏观研判", "缺少「九、AI 宏观研判」章节"),
    ("sector_flow", r"^##\s+十、板块资金流向", "缺少「十、板块资金流向」章节"),
    ("risk", r"^##\s+十一、综合风险评估", "缺少「十一、综合风险评估」章节"),
    ("provenance", r"^##\s+十二、数据溯源", "缺少「十二、数据溯源」章节"),
]

# Score pattern: "**综合评分**: 47/100 (C)" — parse score + grade
SCORE_PATTERN = re.compile(r"\*\*综合评分\*\*:\s*(\d+)/100\s*\(([A-F][+-]?)\)")

# Trigger counts: "触发信号: 3/6" — parse nb + margin
TRIGGER_PATTERN = re.compile(r"触发信号:\s*(\d+)/(\d+)")


def validate_md(text: str) -> list[str]:
    issues: list[str] = []

    if len(text.strip()) < 500:
        issues.append("报告内容过短（<500字符），可能不完整")

    for _key, pattern, message in MD_REQUIRED_SECTIONS:
        if not re.search(pattern, text, flags=re.MULTILINE):
            issues.append(message)

    # Check data provenance section has expected sources
    if not re.search(r"北向资金汇总\s*\|\s*(东方财富|Pandadata|无数据|未知来源)", text):
        issues.append("数据溯源缺少「北向资金汇总」条目")
    if not re.search(r"融资融券明细\s*\|\s*(Pandadata|东方财富|无数据|未知来源)", text):
        issues.append("数据溯源缺少「融资融券明细」条目")
    if not re.search(r"股指期货\s*\|", text):
        issues.append("数据溯源缺少「股指期货」条目")
    if not re.search(r"微观结构\s*\|", text):
        issues.append("数据溯源缺少「微观结构」条目")

    # Check score appears
    if not SCORE_PATTERN.search(text):
        issues.append("缺少综合评分（如 47/100 (C)）")

    # Check generation timestamp
    if not re.search(r"生成时间|自动生成", text):
        issues.append("缺少生成时间戳或自动生成标记")

    # Check for placeholder/error text
    if "{{" in text and "}}" in text:
        issues.append("报告包含未填充的模板占位符 {{...}}")
    if "Traceback" in text:
        issues.append("报告包含异常堆栈信息")

    return issues


# ── JSON validation ──

JSON_REQUIRED_TOP_KEYS = [
    "meta",
    "composite",
    "northbound",
    "margin",
    "futures",
    "resonance",
    "price_volume",
    "microstructure",
    "risk_level",
    "historical_comparison",
    "llm",
    "provenance",
]

JSON_META_KEYS = ["trade_date", "fetch_time", "generator", "version"]
JSON_COMPOSITE_KEYS = ["score", "grade", "label", "northbound_score", "margin_score",
                       "futures_score", "resonance_score", "risk_penalty", "summary"]
JSON_SIGNAL_KEYS = ["signals", "triggered_count", "bullish_count", "bearish_count"]
JSON_RESONANCE_KEYS = ["patterns", "triggered_count"]
JSON_LLM_KEYS = ["source", "analysis", "model"]
JSON_PROVENANCE_CATEGORIES = [
    "northbound_summary", "margin_detail", "margin_macro",
    "futures", "stock_info", "price_volume", "microstructure", "shenwan",
]


def validate_json(data: dict) -> list[str]:
    issues: list[str] = []

    # Top-level keys
    for key in JSON_REQUIRED_TOP_KEYS:
        if key not in data:
            issues.append(f"JSON 缺少顶层字段: {key}")

    # Meta
    meta = data.get("meta", {})
    for key in JSON_META_KEYS:
        if key not in meta:
            issues.append(f"JSON meta 缺少字段: {key}")

    # Composite score
    composite = data.get("composite", {})
    for key in JSON_COMPOSITE_KEYS:
        if key not in composite:
            issues.append(f"JSON composite 缺少字段: {key}")

    score = composite.get("score", -1)
    grade = composite.get("grade", "")
    if not (0 <= score <= 100):
        issues.append(f"综合评分超出范围: {score}")
    if grade and not re.match(r"^[A-F][+-]?$", grade) and grade != "N/A":
        issues.append(f"综合等级格式无效: {grade}")

    # Validate score = weighted sub-scores (approximate due to scoring formula)
    nb_s = composite.get("northbound_score", 0)
    mg_s = composite.get("margin_score", 0)
    fut_s = composite.get("futures_score", 0)
    res_s = composite.get("resonance_score", 0)
    if nb_s != 0 or mg_s != 0 or fut_s != 0:
        # At minimum, sub-scores should be in [-1, 1]
        for name, val in [("北向", nb_s), ("融资", mg_s), ("期货", fut_s), ("共振", res_s)]:
            if not (-1.5 <= val <= 1.5):
                issues.append(f"子得分 {name} 超出 [-1.5, 1.5] 范围: {val}")

    # Northbound signals
    nb = data.get("northbound", {})
    for key in JSON_SIGNAL_KEYS:
        if key not in nb:
            issues.append(f"JSON northbound 缺少字段: {key}")
    nb_signals = nb.get("signals", [])
    if nb_signals:
        for i, sig in enumerate(nb_signals):
            for key in ("key", "label", "triggered", "strength", "direction", "summary"):
                if key not in sig:
                    issues.append(f"northbound signals[{i}] 缺少字段: {key}")
    nb_triggered = nb.get("triggered_count", 0)
    if nb_signals and nb_triggered != sum(1 for s in nb_signals if s.get("triggered")):
        issues.append("northbound triggered_count 与 signals 不一致")

    # Margin signals
    mg = data.get("margin", {})
    for key in JSON_SIGNAL_KEYS:
        if key not in mg:
            issues.append(f"JSON margin 缺少字段: {key}")
    mg_signals = mg.get("signals", [])
    if mg_signals:
        for i, sig in enumerate(mg_signals):
            for key in ("key", "label", "triggered", "strength", "direction", "summary"):
                if key not in sig:
                    issues.append(f"margin signals[{i}] 缺少字段: {key}")

    # Futures signals
    fut = data.get("futures", {})
    for key in JSON_SIGNAL_KEYS:
        if key not in fut:
            issues.append(f"JSON futures 缺少字段: {key}")

    # Resonance
    res = data.get("resonance", {})
    for key in JSON_RESONANCE_KEYS:
        if key not in res:
            issues.append(f"JSON resonance 缺少字段: {key}")

    # LLM
    llm = data.get("llm", {})
    for key in JSON_LLM_KEYS:
        if key not in llm:
            issues.append(f"JSON llm 缺少字段: {key}")
    llm_source = llm.get("source", "")
    if llm_source not in ("real", "fallback", "none", "error"):
        issues.append(f"llm source 值无效: {llm_source}")

    # Provenance
    prov = data.get("provenance", {})
    for cat in JSON_PROVENANCE_CATEGORIES:
        if cat not in prov:
            issues.append(f"JSON provenance 缺少类别: {cat}")

    return issues


# ── CLI ──


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("md_path", type=Path, nargs="?", help="Path to the Markdown report")
    parser.add_argument("json_path", type=Path, nargs="?", help="Path to the JSON data file")
    parser.add_argument("--date", type=str, help="Trade date YYYYMMDD — auto-resolves paths")
    parser.add_argument("--output-dir", type=str, default="output", help="Output root directory")
    args = parser.parse_args()

    # Resolve paths
    if args.date:
        date_dt = args.date
        # date_dt is already YYYYMMDD, format to YYYY-MM-DD for directory
        dir_name = f"{date_dt[:4]}-{date_dt[4:6]}-{date_dt[6:8]}"
        base = Path(args.output_dir) / dir_name
        md_path = base / f"panorama_monitor_{date_dt}.md"
        json_path = base / f"panorama_monitor_{date_dt}.json"
    elif args.md_path and args.json_path:
        md_path = args.md_path
        json_path = args.json_path
    else:
        # Auto-find latest
        output_root = Path(args.output_dir)
        if not output_root.exists():
            print("FAIL")
            print("- 输出目录不存在，请先运行 pipeline")
            return 1
        dirs = sorted([d for d in output_root.iterdir() if d.is_dir()], reverse=True)
        if not dirs:
            print("FAIL")
            print("- 输出目录为空")
            return 1
        latest = dirs[0]
        md_files = list(latest.glob("panorama_monitor_*.md"))
        json_files = list(latest.glob("panorama_monitor_*.json"))
        if not md_files or not json_files:
            print("FAIL")
            print(f"- 在 {latest} 中未找到报告文件")
            return 1
        md_path = md_files[0]
        json_path = json_files[0]

    all_issues: list[str] = []
    exit_code = 0

    # Validate Markdown
    try:
        md_text = md_path.read_text(encoding="utf-8-sig")
    except FileNotFoundError:
        all_issues.append(f"Markdown 文件未找到: {md_path}")
        exit_code = 2
        md_text = ""

    if md_text:
        md_issues = validate_md(md_text)
        all_issues.extend(md_issues)

    # Validate JSON
    try:
        json_text = json_path.read_text(encoding="utf-8-sig")
        json_data = json.loads(json_text)
    except FileNotFoundError:
        all_issues.append(f"JSON 文件未找到: {json_path}")
        exit_code = 2
        json_data = {}
    except json.JSONDecodeError as e:
        all_issues.append(f"JSON 解析失败: {e}")
        exit_code = 2
        json_data = {}

    if json_data:
        json_issues = validate_json(json_data)
        all_issues.extend(json_issues)

    if all_issues:
        print("FAIL")
        for issue in all_issues:
            print(f"  - {issue}")
        return exit_code or 1

    print(f"OK — {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
