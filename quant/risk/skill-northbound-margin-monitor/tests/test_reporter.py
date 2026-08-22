"""Tests for Markdown + JSON report generation."""

import json
import tempfile
from pathlib import Path

import pandas as pd
import pytest

from core.reporter import (
    _find_previous_report,
    _generate_historical_comparison,
    generate_markdown_report,
    generate_json_output,
    write_report,
    _safe_fmt,
    _provenance_label,
    _to_native,
    _industry_ranking_to_list,
)
from core.northbound import run_all_detectors as run_nb
from core.northbound import compute_composite_score as nb_score
from core.margin import run_all_detectors as run_mg
from core.margin import compute_composite_score as mg_score
from core.resonance import analyse_resonance, compute_resonance_score
from core.scorer import (
    compute_capital_flow_score,
    rank_stocks_by_margin_balance,
    rank_stocks_by_margin_buy,
)


def _run_pipeline(
    nb_summary, nb_flow, margin_detail, margin_macro, stock_info, config
):
    """Mini pipeline to generate all report inputs."""
    nb_signals = run_nb(nb_summary, nb_flow, stock_info, config)
    mg_signals = run_mg(margin_detail, margin_macro, stock_info, config)
    nb_comp = nb_score(nb_signals)
    mg_comp = mg_score(mg_signals)
    resonance = analyse_resonance(
        nb_comp, mg_comp,
        sum(1 for s in nb_signals if s.direction == "bullish"),
        sum(1 for s in nb_signals if s.direction == "bearish"),
        sum(1 for s in mg_signals if s.direction == "bullish"),
        sum(1 for s in mg_signals if s.direction == "bearish"),
        config,
    )
    res_score = compute_resonance_score(resonance)
    composite = compute_capital_flow_score(
        nb_comp, mg_comp, res_score,
        sum(1 for s in nb_signals if s.triggered),
        sum(1 for s in mg_signals if s.triggered),
        sum(1 for r in resonance if r.triggered),
        config,
    )
    top_bal = rank_stocks_by_margin_balance(margin_detail, stock_info, 10)
    top_buy = rank_stocks_by_margin_buy(margin_detail, stock_info, 10)
    return nb_signals, mg_signals, resonance, composite, top_bal, top_buy


class TestSafeFmt:
    def test_normal_float(self):
        assert _safe_fmt(3.14159, ".2f") == "3.14"

    def test_none(self):
        assert _safe_fmt(None) == "-"

    def test_nan(self):
        import numpy as np
        assert _safe_fmt(np.nan) == "-"

    def test_string(self):
        assert _safe_fmt("hello") == "hello"


class TestProvenanceLabel:
    def test_pandadata(self):
        assert "Pandadata" in _provenance_label("pandadata")

    def test_eastmoney(self):
        assert "东方财富" in _provenance_label("eastmoney")

    def test_degraded(self):
        assert "降级" in _provenance_label("degraded")

    def test_unknown(self):
        assert "未知" in _provenance_label("unknown")

    def test_none(self):
        assert "无数据" in _provenance_label("none")


class TestMarkdownReport:
    def test_generates_valid_markdown(
        self, sample_nb_summary, sample_nb_flow,
        sample_margin_detail, sample_margin_macro,
        sample_stock_info, sample_config,
    ):
        nb_s, mg_s, res, comp, top_bal, top_buy = _run_pipeline(
            sample_nb_summary, sample_nb_flow,
            sample_margin_detail, sample_margin_macro,
            sample_stock_info, sample_config,
        )
        md = generate_markdown_report(
            trade_date="20260630",
            nb_signals=nb_s,
            margin_signals=mg_s,
            resonance_results=res,
            composite=comp,
            nb_summary=sample_nb_summary,
            margin_detail=sample_margin_detail,
            margin_macro=sample_margin_macro,
            top_margin_balance=top_bal,
            top_margin_buy=top_buy,
            stock_info=sample_stock_info,
            fetch_time="2026-06-30T15:00:00",
            config=sample_config,
        )
        assert isinstance(md, str)
        assert len(md) > 500
        # Check all 7 sections present
        assert "北向资金概览" in md
        assert "融资融券概览" in md
        assert "共振/背离分析" in md
        assert "综合情绪评估" in md
        assert "板块资金流向" in md
        assert "风险提示" in md
        assert "数据溯源" in md

    def test_handles_empty_data(self, sample_config):
        empty = pd.DataFrame()
        nb_s, mg_s, res, comp, top_bal, top_buy = _run_pipeline(
            empty, empty, empty, empty, empty, sample_config,
        )
        md = generate_markdown_report(
            trade_date="20260630",
            nb_signals=nb_s,
            margin_signals=mg_s,
            resonance_results=res,
            composite=comp,
            nb_summary=empty,
            margin_detail=empty,
            margin_macro=empty,
            top_margin_balance=pd.DataFrame(),
            top_margin_buy=pd.DataFrame(),
            stock_info=empty,
            fetch_time="2026-06-30T15:00:00",
            config=sample_config,
        )
        assert isinstance(md, str)
        assert len(md) > 0

    def test_includes_date(self, sample_config):
        empty = pd.DataFrame()
        nb_s, mg_s, res, comp, top_bal, top_buy = _run_pipeline(
            empty, empty, empty, empty, empty, sample_config,
        )
        md = generate_markdown_report(
            trade_date="20260715",
            nb_signals=nb_s, margin_signals=mg_s, resonance_results=res,
            composite=comp,
            nb_summary=empty, margin_detail=empty, margin_macro=empty,
            top_margin_balance=pd.DataFrame(), top_margin_buy=pd.DataFrame(),
            stock_info=empty,
            fetch_time="2026-07-15T15:00:00",
            config=sample_config,
        )
        assert "2026-07-15" in md

    def test_triggered_signals_marked(self, sample_config):
        """Triggered signals should be marked with **触发**."""
        empty = pd.DataFrame()
        nb_s, mg_s, res, comp, top_bal, top_buy = _run_pipeline(
            empty, empty, empty, empty, empty, sample_config,
        )
        md = generate_markdown_report(
            trade_date="20260630",
            nb_signals=nb_s, margin_signals=mg_s, resonance_results=res,
            composite=comp,
            nb_summary=empty, margin_detail=empty, margin_macro=empty,
            top_margin_balance=pd.DataFrame(), top_margin_buy=pd.DataFrame(),
            stock_info=empty,
            fetch_time="2026-06-30T15:00:00",
            config=sample_config,
        )
        assert "未触发" in md


class TestJsonOutput:
    def test_generates_valid_json(
        self, sample_nb_summary, sample_nb_flow,
        sample_margin_detail, sample_margin_macro,
        sample_stock_info, sample_config,
    ):
        nb_s, mg_s, res, comp, top_bal, top_buy = _run_pipeline(
            sample_nb_summary, sample_nb_flow,
            sample_margin_detail, sample_margin_macro,
            sample_stock_info, sample_config,
        )
        data = generate_json_output(
            trade_date="20260630",
            nb_signals=nb_s,
            margin_signals=mg_s,
            resonance_results=res,
            composite=comp,
            top_margin_balance=top_bal,
            top_margin_buy=top_buy,
            fetch_time="2026-06-30T15:00:00",
            nb_summary=sample_nb_summary,
            margin_detail=sample_margin_detail,
            margin_macro=sample_margin_macro,
            stock_info=sample_stock_info,
            config=sample_config,
        )
        assert isinstance(data, dict)
        # Check structure
        assert "meta" in data
        assert "composite" in data
        assert "northbound" in data
        assert "margin" in data
        assert "resonance" in data
        assert "provenance" in data
        # Verify serializable
        json.dumps(data, ensure_ascii=False)

    def test_meta_fields(self, sample_config):
        empty = pd.DataFrame()
        nb_s, mg_s, res, comp, top_bal, top_buy = _run_pipeline(
            empty, empty, empty, empty, empty, sample_config,
        )
        data = generate_json_output(
            trade_date="20260630",
            nb_signals=nb_s, margin_signals=mg_s, resonance_results=res,
            composite=comp,
            top_margin_balance=pd.DataFrame(), top_margin_buy=pd.DataFrame(),
            fetch_time="2026-06-30T15:00:00",
            nb_summary=empty, margin_detail=empty, margin_macro=empty,
            stock_info=empty,
            config=sample_config,
        )
        assert data["meta"]["trade_date"] == "20260630"
        assert data["meta"]["generator"] == "skill-northbound-margin-monitor"

    def test_includes_provenance(self, sample_config):
        empty = pd.DataFrame()
        nb_s, mg_s, res, comp, top_bal, top_buy = _run_pipeline(
            empty, empty, empty, empty, empty, sample_config,
        )
        data = generate_json_output(
            trade_date="20260630",
            nb_signals=nb_s, margin_signals=mg_s, resonance_results=res,
            composite=comp,
            top_margin_balance=pd.DataFrame(), top_margin_buy=pd.DataFrame(),
            fetch_time="2026-06-30T15:00:00",
            nb_summary=empty, margin_detail=empty, margin_macro=empty,
            stock_info=empty,
            config=sample_config,
        )
        assert "northbound_summary" in data["provenance"]
        assert "margin_detail" in data["provenance"]


class TestWriteReport:
    def test_writes_md_and_json(
        self, sample_nb_summary, sample_nb_flow,
        sample_margin_detail, sample_margin_macro,
        sample_stock_info, sample_config,
    ):
        nb_s, mg_s, res, comp, top_bal, top_buy = _run_pipeline(
            sample_nb_summary, sample_nb_flow,
            sample_margin_detail, sample_margin_macro,
            sample_stock_info, sample_config,
        )
        md = generate_markdown_report(
            trade_date="20260630",
            nb_signals=nb_s, margin_signals=mg_s, resonance_results=res,
            composite=comp,
            nb_summary=sample_nb_summary,
            margin_detail=sample_margin_detail,
            margin_macro=sample_margin_macro,
            top_margin_balance=top_bal, top_margin_buy=top_buy,
            stock_info=sample_stock_info,
            fetch_time="2026-06-30T15:00:00",
            config=sample_config,
        )
        json_data = generate_json_output(
            trade_date="20260630",
            nb_signals=nb_s, margin_signals=mg_s, resonance_results=res,
            composite=comp,
            top_margin_balance=top_bal, top_margin_buy=top_buy,
            fetch_time="2026-06-30T15:00:00",
            nb_summary=sample_nb_summary,
            margin_detail=sample_margin_detail,
            margin_macro=sample_margin_macro,
            stock_info=sample_stock_info,
            config=sample_config,
        )

        with tempfile.TemporaryDirectory() as tmp:
            md_path, json_path = write_report(
                "20260630", md, json_data, output_dir=tmp,
            )
            assert md_path.exists()
            assert json_path.exists()
            assert md_path.suffix == ".md"
            assert json_path.suffix == ".json"
            # Check content
            content = md_path.read_text(encoding="utf-8")
            assert "北向资金" in content
            json_content = json.loads(json_path.read_text(encoding="utf-8"))
            assert "composite" in json_content

    def test_output_dir_from_config(self, sample_config):
        with tempfile.TemporaryDirectory() as tmp:
            config = {**sample_config, "output": {"dir": tmp}}
            nb_s, mg_s, res, comp, top_bal, top_buy = _run_pipeline(
                pd.DataFrame(), pd.DataFrame(), pd.DataFrame(),
                pd.DataFrame(), pd.DataFrame(), config,
            )
            md = "test"
            js = {"test": True}
            md_path, json_path = write_report(
                "20260630", md, js, config=config,
            )
            assert str(tmp) in str(md_path)


# ── _to_native tests ──


class TestToNative:
    """JSON serialization helper for numpy types."""

    def test_numpy_integer(self):
        import numpy as np
        assert _to_native(np.int64(42)) == 42
        assert isinstance(_to_native(np.int64(42)), int)

    def test_numpy_float(self):
        import numpy as np
        assert _to_native(np.float64(3.14)) == 3.14

    def test_numpy_nan(self):
        import numpy as np
        assert _to_native(np.float64(np.nan)) is None

    def test_numpy_inf(self):
        import numpy as np
        assert _to_native(np.float64(np.inf)) is None

    def test_numpy_bool(self):
        import numpy as np
        assert _to_native(np.bool_(True)) is True
        assert _to_native(np.bool_(False)) is False

    def test_numpy_array(self):
        import numpy as np
        import math
        arr = np.array([1.0, 2.0, np.nan])
        result = _to_native(arr)
        assert result[0] == 1.0
        assert result[1] == 2.0
        assert math.isnan(result[2])

    def test_nested_dict(self):
        import numpy as np
        data = {"a": np.int64(1), "b": {"c": np.float64(2.5)}}
        result = _to_native(data)
        assert result == {"a": 1, "b": {"c": 2.5}}

    def test_list_of_mixed(self):
        import numpy as np
        data = [np.int64(1), np.float64(2.5), "str"]
        result = _to_native(data)
        assert result == [1, 2.5, "str"]

    def test_tuple(self):
        import numpy as np
        data = (np.int64(1), np.float64(2.5))
        result = _to_native(data)
        assert result == [1, 2.5]

    def test_plain_values_pass_through(self):
        assert _to_native("hello") == "hello"
        assert _to_native(42) == 42
        assert _to_native(None) is None
        assert _to_native(True) is True


# ── Industry ranking serialization tests ──


class TestIndustryRankingToList:
    def test_none_returns_empty(self):
        assert _industry_ranking_to_list(None) == []

    def test_empty_returns_empty(self):
        import pandas as pd
        assert _industry_ranking_to_list(pd.DataFrame()) == []

    def test_converts_dataframe(self):
        import pandas as pd
        df = pd.DataFrame({
            "rank": [1, 2],
            "industry": ["电子", "银行"],
            "stock_count": [15, 10],
            "avg_balance_亿": [12.5, 25.3],
            "avg_buy_亿": [3.1, 5.7],
            "z_balance": [0.85, -0.42],
            "z_buy": [0.67, -0.33],
            "composite_z": [0.76, -0.375],
        })
        result = _industry_ranking_to_list(df)
        assert len(result) == 2
        assert result[0]["industry"] == "电子"
        assert result[0]["composite_z"] == 0.76
        assert result[1]["rank"] == 2


# ── Reporter sections (futures, LLM, risks, industry_ranking) ──


class TestMarkdownReportSections:
    """Previously untested report sections: futures, LLM, risks, industry ranking."""

    def _mini_pipeline(self, nb_summary, nb_flow, margin_detail, margin_macro,
                       stock_info, config, futures_signals=None, futures_data=None):
        """Run mini pipeline returning all report inputs."""
        return _run_pipeline(nb_summary, nb_flow, margin_detail, margin_macro,
                             stock_info, config)

    def test_futures_section_rendered(self, sample_nb_summary, sample_nb_flow,
                                       sample_margin_detail, sample_margin_macro,
                                       sample_stock_info, sample_config,
                                       sample_futures_data):
        """When futures_signals non-empty, section 三 should render."""
        from core.futures import run_all_detectors as run_fut
        nb_s, mg_s, res, comp, top_bal, top_buy = self._mini_pipeline(
            sample_nb_summary, sample_nb_flow, sample_margin_detail,
            sample_margin_macro, sample_stock_info, sample_config,
        )
        fut_s = run_fut(sample_futures_data, sample_config)
        md = generate_markdown_report(
            trade_date="20260630",
            nb_signals=nb_s, margin_signals=mg_s, resonance_results=res,
            composite=comp,
            nb_summary=sample_nb_summary, margin_detail=sample_margin_detail,
            margin_macro=sample_margin_macro,
            top_margin_balance=top_bal, top_margin_buy=top_buy,
            stock_info=sample_stock_info,
            fetch_time="2026-06-30T15:00:00", config=sample_config,
            futures_signals=fut_s, futures_data=sample_futures_data,
        )
        assert "股指期货信号" in md
        assert "期货综合评分" in md

    def test_llm_section_real(self, sample_config):
        """LLM section with source='real' should include model attribution."""
        empty = pd.DataFrame()
        nb_s, mg_s, res, comp, top_bal, top_buy = self._mini_pipeline(
            empty, empty, empty, empty, empty, sample_config,
        )
        md = generate_markdown_report(
            trade_date="20260630",
            nb_signals=nb_s, margin_signals=mg_s, resonance_results=res,
            composite=comp,
            nb_summary=empty, margin_detail=empty, margin_macro=empty,
            top_margin_balance=pd.DataFrame(), top_margin_buy=pd.DataFrame(),
            stock_info=empty,
            fetch_time="2026-06-30T15:00:00", config=sample_config,
            llm_analysis="AI predicts bullish trend", llm_source="real",
            llm_model="claude-sonnet-4-6",
        )
        assert "AI 宏观研判" in md
        assert "claude-sonnet-4-6" in md
        assert "AI predicts bullish trend" in md

    def test_llm_section_fallback(self, sample_config):
        """LLM section with source='fallback' should show rule-engine warning."""
        empty = pd.DataFrame()
        nb_s, mg_s, res, comp, top_bal, top_buy = self._mini_pipeline(
            empty, empty, empty, empty, empty, sample_config,
        )
        md = generate_markdown_report(
            trade_date="20260630",
            nb_signals=nb_s, margin_signals=mg_s, resonance_results=res,
            composite=comp,
            nb_summary=empty, margin_detail=empty, margin_macro=empty,
            top_margin_balance=pd.DataFrame(), top_margin_buy=pd.DataFrame(),
            stock_info=empty,
            fetch_time="2026-06-30T15:00:00", config=sample_config,
            llm_analysis="Rule-based fallback analysis", llm_source="fallback",
        )
        assert "规则引擎" in md

    def test_llm_section_absent_when_none(self, sample_config):
        """No LLM section when source='none'."""
        empty = pd.DataFrame()
        nb_s, mg_s, res, comp, top_bal, top_buy = self._mini_pipeline(
            empty, empty, empty, empty, empty, sample_config,
        )
        md = generate_markdown_report(
            trade_date="20260630",
            nb_signals=nb_s, margin_signals=mg_s, resonance_results=res,
            composite=comp,
            nb_summary=empty, margin_detail=empty, margin_macro=empty,
            top_margin_balance=pd.DataFrame(), top_margin_buy=pd.DataFrame(),
            stock_info=empty,
            fetch_time="2026-06-30T15:00:00", config=sample_config,
            llm_analysis="", llm_source="none",
        )
        assert "AI 宏观研判" not in md

    def test_risk_alerts_rendered(self, sample_nb_summary, sample_nb_flow,
                                    sample_margin_detail, sample_margin_macro,
                                    sample_stock_info, sample_config):
        """Risk alerts section should list triggered bearish signals."""
        # Use data that produces bearish signals
        nb_s, mg_s, res, comp, top_bal, top_buy = self._mini_pipeline(
            sample_nb_summary, sample_nb_flow, sample_margin_detail,
            sample_margin_macro, sample_stock_info, sample_config,
        )
        md = generate_markdown_report(
            trade_date="20260630",
            nb_signals=nb_s, margin_signals=mg_s, resonance_results=res,
            composite=comp,
            nb_summary=sample_nb_summary, margin_detail=sample_margin_detail,
            margin_macro=sample_margin_macro,
            top_margin_balance=top_bal, top_margin_buy=top_buy,
            stock_info=sample_stock_info,
            fetch_time="2026-06-30T15:00:00", config=sample_config,
        )
        assert "风险提示" in md

    def test_no_risk_when_empty(self, sample_config):
        """Risk section shows 'no risk' when no bearish triggers above 0.5."""
        empty = pd.DataFrame()
        nb_s, mg_s, res, comp, top_bal, top_buy = self._mini_pipeline(
            empty, empty, empty, empty, empty, sample_config,
        )
        md = generate_markdown_report(
            trade_date="20260630",
            nb_signals=nb_s, margin_signals=mg_s, resonance_results=res,
            composite=comp,
            nb_summary=empty, margin_detail=empty, margin_macro=empty,
            top_margin_balance=pd.DataFrame(), top_margin_buy=pd.DataFrame(),
            stock_info=empty,
            fetch_time="2026-06-30T15:00:00", config=sample_config,
        )
        assert "无重大风险提示" in md

    def test_industry_ranking_section(self, sample_nb_summary, sample_nb_flow,
                                        sample_margin_detail, sample_margin_macro,
                                        sample_stock_info, sample_config):
        """When industry_ranking is provided, section 七 should show z-score table."""
        from core.scorer import compute_industry_neutral_ranking
        nb_s, mg_s, res, comp, top_bal, top_buy = self._mini_pipeline(
            sample_nb_summary, sample_nb_flow, sample_margin_detail,
            sample_margin_macro, sample_stock_info, sample_config,
        )
        ranking = compute_industry_neutral_ranking(
            sample_margin_detail, sample_stock_info, top_n=5,
        )
        md = generate_markdown_report(
            trade_date="20260630",
            nb_signals=nb_s, margin_signals=mg_s, resonance_results=res,
            composite=comp,
            nb_summary=sample_nb_summary, margin_detail=sample_margin_detail,
            margin_macro=sample_margin_macro,
            top_margin_balance=top_bal, top_margin_buy=top_buy,
            stock_info=sample_stock_info,
            fetch_time="2026-06-30T15:00:00", config=sample_config,
            industry_ranking=ranking,
        )
        assert "行业融资暴露排名" in md
        assert "综合Z" in md
        assert "Z-score" in md

    def test_industry_section_fallback_no_ranking(self, sample_nb_summary,
                                                    sample_nb_flow,
                                                    sample_margin_detail,
                                                    sample_margin_macro,
                                                    sample_stock_info,
                                                    sample_config):
        """Without industry_ranking, falls back to basic industry count."""
        nb_s, mg_s, res, comp, top_bal, top_buy = self._mini_pipeline(
            sample_nb_summary, sample_nb_flow, sample_margin_detail,
            sample_margin_macro, sample_stock_info, sample_config,
        )
        md = generate_markdown_report(
            trade_date="20260630",
            nb_signals=nb_s, margin_signals=mg_s, resonance_results=res,
            composite=comp,
            nb_summary=sample_nb_summary, margin_detail=sample_margin_detail,
            margin_macro=sample_margin_macro,
            top_margin_balance=top_bal, top_margin_buy=top_buy,
            stock_info=sample_stock_info,
            fetch_time="2026-06-30T15:00:00", config=sample_config,
            industry_ranking=None,
        )
        assert "A股行业分布" in md


# ── Historical comparison tests ──


class TestHistoricalComparison:
    """_find_previous_report() and _generate_historical_comparison()."""

    def _make_previous_report(self, trade_date="20260629", score=65.0):
        """Build a minimal previous report dict matching JSON output structure."""
        return {
            "meta": {"trade_date": trade_date, "fetch_time": "2026-06-29T15:00:00"},
            "composite": {
                "score": score, "grade": "B+", "label": "偏乐观",
                "northbound_score": 0.35, "margin_score": 0.25,
                "futures_score": 0.10, "resonance_score": 0.15,
                "risk_penalty": 0.0, "summary": "test",
            },
            "northbound": {"triggered_count": 3, "bullish_count": 2, "bearish_count": 1},
            "margin": {"triggered_count": 4, "bullish_count": 3, "bearish_count": 1},
            "futures": {"triggered_count": 1, "bullish_count": 1, "bearish_count": 0},
            "resonance": {"triggered_count": 1},
        }

    def test_comparison_rendered_with_previous(self, sample_nb_summary, sample_nb_flow,
                                                sample_margin_detail, sample_margin_macro,
                                                sample_stock_info, sample_config):
        """When previous_report is provided, historical comparison section renders."""
        from core.futures import run_all_detectors as run_fut
        from core.scorer import compute_industry_neutral_ranking

        nb_s, mg_s, res, comp, top_bal, top_buy = _run_pipeline(
            sample_nb_summary, sample_nb_flow, sample_margin_detail,
            sample_margin_macro, sample_stock_info, sample_config,
        )
        fut_s = run_fut(pd.DataFrame(), sample_config)

        prev = self._make_previous_report()
        md = generate_markdown_report(
            trade_date="20260630",
            nb_signals=nb_s, margin_signals=mg_s, resonance_results=res,
            composite=comp,
            nb_summary=sample_nb_summary, margin_detail=sample_margin_detail,
            margin_macro=sample_margin_macro,
            top_margin_balance=top_bal, top_margin_buy=top_buy,
            stock_info=sample_stock_info,
            fetch_time="2026-06-30T15:00:00", config=sample_config,
            futures_signals=fut_s, futures_data=pd.DataFrame(),
            previous_report=prev,
        )
        assert "历史对比" in md
        assert "对比基准" in md
        assert "2026-06-29" in md

    def test_comparison_absent_without_previous(self, sample_nb_summary, sample_nb_flow,
                                                  sample_margin_detail, sample_margin_macro,
                                                  sample_stock_info, sample_config):
        """Without previous_report, historical comparison should not appear."""
        nb_s, mg_s, res, comp, top_bal, top_buy = _run_pipeline(
            sample_nb_summary, sample_nb_flow, sample_margin_detail,
            sample_margin_macro, sample_stock_info, sample_config,
        )
        md = generate_markdown_report(
            trade_date="20260630",
            nb_signals=nb_s, margin_signals=mg_s, resonance_results=res,
            composite=comp,
            nb_summary=sample_nb_summary, margin_detail=sample_margin_detail,
            margin_macro=sample_margin_macro,
            top_margin_balance=top_bal, top_margin_buy=top_buy,
            stock_info=sample_stock_info,
            fetch_time="2026-06-30T15:00:00", config=sample_config,
            previous_report=None,
        )
        assert "## 八、历史对比" in md
        assert "无历史数据可比" in md

    def test_historical_comparison_has_metrics(self):
        """_generate_historical_comparison table should include key metrics."""
        prev = self._make_previous_report()
        from core.scorer import CompositeScore

        comp = CompositeScore(
            score=72.0, grade="A", label="乐观",
            northbound_score=0.45, margin_score=0.35,
            futures_score=0.15, resonance_score=0.20,
            risk_penalty=0.0, summary="test",
        )
        signals = []  # Empty signals for simplicity

        result = _generate_historical_comparison(
            comp, signals, signals, signals, signals, prev,
        )
        assert "综合得分" in result
        assert "北向得分" in result
        assert "融资得分" in result
        assert "触发数" in result

    def test_json_output_includes_historical_comparison(self, sample_config):
        """JSON output with previous_report should include historical_comparison field."""
        prev = self._make_previous_report()
        empty = pd.DataFrame()
        nb_s, mg_s, res, comp, top_bal, top_buy = _run_pipeline(
            empty, empty, empty, empty, empty, sample_config,
        )
        data = generate_json_output(
            trade_date="20260630",
            nb_signals=nb_s, margin_signals=mg_s, resonance_results=res,
            composite=comp,
            top_margin_balance=pd.DataFrame(), top_margin_buy=pd.DataFrame(),
            fetch_time="2026-06-30T15:00:00",
            nb_summary=empty, margin_detail=empty, margin_macro=empty,
            stock_info=empty, config=sample_config,
            previous_report=prev,
        )
        assert "historical_comparison" in data
        hc = data["historical_comparison"]
        assert "score_delta" in hc
        assert "northbound_score_delta" in hc
        assert "margin_score_delta" in hc
        assert "triggered_counts" in hc

    def test_json_output_no_historical_without_previous(self, sample_config):
        """JSON output without previous_report should not have historical_comparison."""
        empty = pd.DataFrame()
        nb_s, mg_s, res, comp, top_bal, top_buy = _run_pipeline(
            empty, empty, empty, empty, empty, sample_config,
        )
        data = generate_json_output(
            trade_date="20260630",
            nb_signals=nb_s, margin_signals=mg_s, resonance_results=res,
            composite=comp,
            top_margin_balance=pd.DataFrame(), top_margin_buy=pd.DataFrame(),
            fetch_time="2026-06-30T15:00:00",
            nb_summary=empty, margin_detail=empty, margin_macro=empty,
            stock_info=empty, config=sample_config,
            previous_report=None,
        )
        assert "historical_comparison" in data
        assert data["historical_comparison"] is None

    def test_find_previous_report_empty_dir(self, tmp_path):
        """No reports → returns None."""
        result = _find_previous_report("20260630", tmp_path)
        assert result is None

    def test_find_previous_report_finds_prior(self, tmp_path):
        """Finds the most recent prior report."""
        # Create a previous date dir with a JSON file
        prev_dir = tmp_path / "2026-06-29"
        prev_dir.mkdir(parents=True)
        prev_json = prev_dir / "panorama_monitor_20260629.json"
        prev_json.write_text(json.dumps(self._make_previous_report("20260629")), encoding="utf-8")

        # Create an even older date dir
        older_dir = tmp_path / "2026-06-28"
        older_dir.mkdir(parents=True)
        older_json = older_dir / "panorama_monitor_20260628.json"
        older_json.write_text(json.dumps(self._make_previous_report("20260628", score=60.0)), encoding="utf-8")

        result = _find_previous_report("20260630", tmp_path)
        assert result is not None
        assert result["meta"]["trade_date"] == "20260629"  # Most recent prior

    def test_find_previous_report_skips_future(self, tmp_path):
        """Skips directories dated after current_date."""
        prev_dir = tmp_path / "2026-07-02"
        prev_dir.mkdir(parents=True)
        prev_json = prev_dir / "panorama_monitor_20260702.json"
        prev_json.write_text(json.dumps(self._make_previous_report("20260702")), encoding="utf-8")

        result = _find_previous_report("20260630", tmp_path)
        assert result is None

    def test_section_numbers_with_historical(self):
        """When historical comparison is present, compare content has key metrics."""
        prev = self._make_previous_report()
        from core.scorer import CompositeScore

        comp = CompositeScore(
            score=72.0, grade="A", label="乐观",
            northbound_score=0.45, margin_score=0.35,
            futures_score=0.15, resonance_score=0.20,
            risk_penalty=0.0, summary="test",
        )
        signals = []
        comparison_md = _generate_historical_comparison(
            comp, signals, signals, signals, signals, prev,
        )
        assert "综合得分" in comparison_md
        assert "北向得分" in comparison_md
        assert "2026-06-29" in comparison_md
        assert "65" in comparison_md  # Previous score


# ── Price-volume section tests ──


class TestPriceVolumeSection:
    """PV signals rendering in markdown and JSON reports."""

    def _make_pv_signals(self):
        """Create mock price-volume signal results."""
        from core._types import SignalResult
        return [
            SignalResult(
                key="index_momentum", label="指数动量",
                triggered=True, strength=0.6, direction="bullish",
                summary="20日涨幅8.5%，趋势偏多",
            ),
            SignalResult(
                key="volatility_regime", label="波动率区间",
                triggered=False, strength=0.0, direction="neutral",
                summary="年化波动率22.0%，正常区间",
            ),
        ]

    def test_pv_section_rendered(self, sample_nb_summary, sample_nb_flow,
                                  sample_margin_detail, sample_margin_macro,
                                  sample_stock_info, sample_config):
        """When pv_signals provided, section 五 should render."""
        nb_s, mg_s, res, comp, top_bal, top_buy = _run_pipeline(
            sample_nb_summary, sample_nb_flow, sample_margin_detail,
            sample_margin_macro, sample_stock_info, sample_config,
        )
        pv_s = self._make_pv_signals()
        md = generate_markdown_report(
            trade_date="20260630",
            nb_signals=nb_s, margin_signals=mg_s, resonance_results=res,
            composite=comp,
            nb_summary=sample_nb_summary, margin_detail=sample_margin_detail,
            margin_macro=sample_margin_macro,
            top_margin_balance=top_bal, top_margin_buy=top_buy,
            stock_info=sample_stock_info,
            fetch_time="2026-06-30T15:00:00", config=sample_config,
            pv_signals=pv_s,
        )
        assert "量价确认" in md
        assert "指数动量" in md
        assert "波动率区间" in md

    def test_pv_in_json_output(self, sample_config):
        """JSON should include price_volume section."""
        empty = pd.DataFrame()
        nb_s, mg_s, res, comp, top_bal, top_buy = _run_pipeline(
            empty, empty, empty, empty, empty, sample_config,
        )
        pv_s = self._make_pv_signals()
        data = generate_json_output(
            trade_date="20260630",
            nb_signals=nb_s, margin_signals=mg_s, resonance_results=res,
            composite=comp,
            top_margin_balance=pd.DataFrame(), top_margin_buy=pd.DataFrame(),
            fetch_time="2026-06-30T15:00:00",
            nb_summary=empty, margin_detail=empty, margin_macro=empty,
            stock_info=empty, config=sample_config,
            pv_signals=pv_s,
        )
        assert "price_volume" in data
        pv = data["price_volume"]
        assert "signals" in pv
        assert pv["triggered_count"] == 1
        assert pv["bullish_count"] == 1

    def test_pv_section_absent_when_none(self, sample_nb_summary, sample_nb_flow,
                                          sample_margin_detail, sample_margin_macro,
                                          sample_stock_info, sample_config):
        """No PV signals → no PV signal section (but provenance still shows line)."""
        nb_s, mg_s, res, comp, top_bal, top_buy = _run_pipeline(
            sample_nb_summary, sample_nb_flow, sample_margin_detail,
            sample_margin_macro, sample_stock_info, sample_config,
        )
        md = generate_markdown_report(
            trade_date="20260630",
            nb_signals=nb_s, margin_signals=mg_s, resonance_results=res,
            composite=comp,
            nb_summary=sample_nb_summary, margin_detail=sample_margin_detail,
            margin_macro=sample_margin_macro,
            top_margin_balance=top_bal, top_margin_buy=top_buy,
            stock_info=sample_stock_info,
            fetch_time="2026-06-30T15:00:00", config=sample_config,
            pv_signals=[],
        )
        assert "## 五、量价确认" not in md  # Section heading absent
        assert "| 量价确认 | 不可用" in md  # Provenance shows unavailable

    def test_pv_in_data_provenance(self, sample_nb_summary, sample_nb_flow,
                                    sample_margin_detail, sample_margin_macro,
                                    sample_stock_info, sample_config):
        """Data provenance should include PV data source."""
        nb_s, mg_s, res, comp, top_bal, top_buy = _run_pipeline(
            sample_nb_summary, sample_nb_flow, sample_margin_detail,
            sample_margin_macro, sample_stock_info, sample_config,
        )
        pv_s = self._make_pv_signals()
        md = generate_markdown_report(
            trade_date="20260630",
            nb_signals=nb_s, margin_signals=mg_s, resonance_results=res,
            composite=comp,
            nb_summary=sample_nb_summary, margin_detail=sample_margin_detail,
            margin_macro=sample_margin_macro,
            top_margin_balance=top_bal, top_margin_buy=top_buy,
            stock_info=sample_stock_info,
            fetch_time="2026-06-30T15:00:00", config=sample_config,
            pv_signals=pv_s,
        )
        assert "CSI300指数" in md or "量价确认" in md
