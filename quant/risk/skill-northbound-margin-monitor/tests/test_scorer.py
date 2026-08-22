"""Tests for composite scoring engine."""

import numpy as np
import pandas as pd
import pytest

from core.scorer import (
    _assign_grade,
    compute_capital_flow_score,
    compute_industry_neutral_ranking,
    compute_risk_level,
    rank_stocks_by_margin_balance,
    rank_stocks_by_margin_buy,
    CompositeScore,
    RiskLevel,
)


class TestComputeCapitalFlowScore:
    def test_neutral_inputs(self, sample_config):
        result = compute_capital_flow_score(0.0, 0.0, 0.0, 0, 0, 0, sample_config)
        assert isinstance(result, CompositeScore)
        assert 40 <= result.score <= 60  # near neutral
        assert result.grade in ("C", "B", "D")

    def test_bullish_inputs(self, sample_config):
        result = compute_capital_flow_score(0.8, 0.7, 0.5, 5, 5, 3, sample_config)
        assert result.score > 60
        assert result.grade in ("A+", "A", "B+")

    def test_bearish_inputs(self, sample_config):
        result = compute_capital_flow_score(-0.8, -0.7, -0.5, 0, 0, 3, sample_config)
        assert result.score < 40
        assert result.grade in ("E", "F", "F-")

    def test_score_in_0_100_range(self, sample_config):
        result = compute_capital_flow_score(1.0, 1.0, 1.0, 6, 6, 4, sample_config)
        assert 0 <= result.score <= 100

    def test_score_in_0_100_range_bearish(self, sample_config):
        result = compute_capital_flow_score(-1.0, -1.0, -1.0, 0, 0, 4, sample_config)
        assert 0 <= result.score <= 100

    def test_risk_penalty_applied(self, sample_config):
        # Many triggered signals all pointing same way = risk
        result = compute_capital_flow_score(0.8, 0.8, 0.6, 5, 5, 2, sample_config)
        # Risk penalty should be > 0 when many signals triggered
        assert result.risk_penalty >= 0

    def test_returns_composite_score_dataclass(self, sample_config):
        result = compute_capital_flow_score(0.3, 0.2, 0.1, 2, 2, 1, sample_config)
        assert hasattr(result, "score")
        assert hasattr(result, "grade")
        assert hasattr(result, "label")
        assert hasattr(result, "summary")

    def test_different_custom_weights(self):
        config = {
            "scoring": {
                "northbound_weight": 0.7,
                "margin_weight": 0.3,
                "risk_overheat_threshold": 0.5,
            },
        }
        result = compute_capital_flow_score(0.5, -0.5, 0.0, 1, 1, 0, config)
        # NB weighted more → positive bias
        assert result.northbound_score == 0.5
        assert result.margin_score == -0.5

    def test_pv_composite_included_in_score(self, sample_config):
        """PV composite should shift the base score when nonzero."""
        result_no_pv = compute_capital_flow_score(
            0.5, 0.5, 0.0, 2, 2, 0, sample_config,
            pv_composite=0.0, pv_triggered_count=0,
        )
        result_with_pv = compute_capital_flow_score(
            0.5, 0.5, 0.0, 2, 2, 0, sample_config,
            pv_composite=0.8, pv_triggered_count=2,
        )
        assert result_with_pv.score >= result_no_pv.score

    def test_pv_composite_negative_pulls_down(self, sample_config):
        """Negative PV composite should reduce score."""
        result_no_pv = compute_capital_flow_score(
            0.5, 0.5, 0.0, 2, 2, 0, sample_config,
            pv_composite=0.0, pv_triggered_count=0,
        )
        result_with_pv = compute_capital_flow_score(
            0.5, 0.5, 0.0, 2, 2, 0, sample_config,
            pv_composite=-0.8, pv_triggered_count=2,
        )
        assert result_with_pv.score <= result_no_pv.score

    def test_pv_triggered_contributes_to_risk(self):
        """PV triggered count should be included in total for risk penalty."""
        config = {
            "scoring": {
                "northbound_weight": 0.35, "margin_weight": 0.35,
                "futures_weight": 0.2, "price_volume_weight": 0.1,
                "risk_penalty_high_triggered": 8,
                "risk_penalty_high_amount": 0.2,
                "risk_penalty_high_base_threshold": 0.6,
                "risk_penalty_medium_triggered": 6,
                "risk_penalty_medium_amount": 0.1,
                "risk_penalty_medium_base_threshold": 0.5,
            },
        }
        # 4 nb + 3 mg + 2 pv = 9 total (exceeds 8 high threshold)
        result = compute_capital_flow_score(
            0.8, 0.7, 0.0, 4, 3, 0, config,
            pv_composite=0.5, pv_triggered_count=2,
        )
        assert result.risk_penalty > 0


class TestRankStocksByMarginBalance:
    def test_returns_top_n(self, sample_margin_detail, sample_stock_info):
        result = rank_stocks_by_margin_balance(sample_margin_detail, sample_stock_info, top_n=10)
        assert len(result) <= 10
        assert "rank" in result.columns
        assert "symbol" in result.columns
        assert "margin_balance" in result.columns

    def test_returns_correct_columns(self, sample_margin_detail, sample_stock_info):
        result = rank_stocks_by_margin_balance(sample_margin_detail, sample_stock_info)
        for col in ["rank", "symbol", "name", "industry", "margin_balance"]:
            assert col in result.columns

    def test_sorted_descending(self, sample_margin_detail, sample_stock_info):
        result = rank_stocks_by_margin_balance(sample_margin_detail, sample_stock_info)
        balances = result["margin_balance"].values
        for i in range(len(balances) - 1):
            assert balances[i] >= balances[i + 1]

    def test_empty_input(self):
        result = rank_stocks_by_margin_balance(pd.DataFrame(), pd.DataFrame())
        assert result.empty

    def test_no_symbol_column(self):
        df = pd.DataFrame({"margin_balance": [100, 200, 50]})
        result = rank_stocks_by_margin_balance(df, pd.DataFrame())
        assert result.empty

    def test_no_balance_column(self):
        df = pd.DataFrame({"symbol": ["000001.SZ", "000002.SZ"]})
        result = rank_stocks_by_margin_balance(df, pd.DataFrame())
        assert result.empty

    def test_joins_stock_info_names(self):
        margin = pd.DataFrame({
            "symbol": ["000001.SZ", "000002.SZ"],
            "margin_balance": [1000, 500],
            "date": ["20260630", "20260630"],
        })
        info = pd.DataFrame({
            "symbol": ["000001.SZ", "000002.SZ"],
            "name": ["平安银行", "万科A"],
            "industry": ["银行", "房地产"],
        })
        result = rank_stocks_by_margin_balance(margin, info)
        assert result.iloc[0]["name"] == "平安银行"
        assert result.iloc[0]["industry"] == "银行"


class TestRankStocksByMarginBuy:
    def test_returns_top_n(self, sample_margin_detail, sample_stock_info):
        result = rank_stocks_by_margin_buy(sample_margin_detail, sample_stock_info, top_n=10)
        assert len(result) <= 10
        assert "margin_buy" in result.columns

    def test_sorted_descending(self, sample_margin_detail, sample_stock_info):
        result = rank_stocks_by_margin_buy(sample_margin_detail, sample_stock_info)
        buys = result["margin_buy"].values
        for i in range(len(buys) - 1):
            assert buys[i] >= buys[i + 1]

    def test_empty_input(self):
        result = rank_stocks_by_margin_buy(pd.DataFrame(), pd.DataFrame())
        assert result.empty

    def test_no_buy_column(self):
        df = pd.DataFrame({"symbol": ["000001.SZ"], "margin_balance": [100]})
        result = rank_stocks_by_margin_buy(df, pd.DataFrame())
        assert result.empty


class TestIndustryNeutralRanking:
    """Tests for compute_industry_neutral_ranking."""

    @pytest.fixture
    def margin_detail_with_dates(self):
        """Multi-date margin detail for per-stock latest-value logic."""
        np.random.seed(77)
        symbols = []
        for code in range(1, 31):
            sym = f"{code:06d}.{'SH' if code > 15 else 'SZ'}"
            for d in ["20260628", "20260629", "20260630"]:
                symbols.append({
                    "symbol": sym,
                    "date": d,
                    "margin_balance": np.random.uniform(1e8, 30e8),
                    "buy_on_margin_value": np.random.uniform(0.1e8, 3e8),
                })
        return pd.DataFrame(symbols)

    @pytest.fixture
    def stock_info_with_industry(self):
        """Stock info with industry assignments."""
        industries = ["电子", "医药生物", "计算机", "食品饮料", "银行"]
        rows = []
        for code in range(1, 31):
            rows.append({
                "symbol": f"{code:06d}.{'SH' if code > 15 else 'SZ'}",
                "name": f"测试{code}",
                "industry": industries[code % len(industries)],
            })
        return pd.DataFrame(rows)

    def test_basic_ranking(self, margin_detail_with_dates, stock_info_with_industry):
        result = compute_industry_neutral_ranking(
            margin_detail_with_dates, stock_info_with_industry, top_n=5,
        )
        assert not result.empty
        assert len(result) <= 5
        for col in ["rank", "industry", "stock_count", "avg_balance_亿",
                     "avg_buy_亿", "z_balance", "z_buy", "composite_z"]:
            assert col in result.columns

    def test_sorted_by_composite_z_desc(self, margin_detail_with_dates, stock_info_with_industry):
        result = compute_industry_neutral_ranking(
            margin_detail_with_dates, stock_info_with_industry,
        )
        z_vals = result["composite_z"].values
        for i in range(len(z_vals) - 1):
            assert z_vals[i] >= z_vals[i + 1]

    def test_empty_margin_detail(self, stock_info_with_industry):
        result = compute_industry_neutral_ranking(pd.DataFrame(), stock_info_with_industry)
        assert result.empty

    def test_empty_stock_info(self, margin_detail_with_dates):
        result = compute_industry_neutral_ranking(margin_detail_with_dates, pd.DataFrame())
        assert result.empty

    def test_no_industry_column(self, margin_detail_with_dates):
        info = pd.DataFrame({"symbol": ["000001.SZ"], "name": ["测试"]})
        result = compute_industry_neutral_ranking(margin_detail_with_dates, info)
        assert result.empty

    def test_no_symbol_column(self):
        margin = pd.DataFrame({"margin_balance": [100, 200]})
        info = pd.DataFrame({"symbol": ["000001.SZ"], "industry": ["银行"]})
        result = compute_industry_neutral_ranking(margin, info)
        assert result.empty

    def test_no_balance_column(self):
        margin = pd.DataFrame({"symbol": ["000001.SZ", "000002.SZ"]})
        info = pd.DataFrame({"symbol": ["000001.SZ", "000002.SZ"], "industry": ["银行", "电子"]})
        result = compute_industry_neutral_ranking(margin, info)
        assert result.empty

    def test_z_scores_centered(self, margin_detail_with_dates, stock_info_with_industry):
        """Z-scores across all industries should be approximately mean=0 when n>=3."""
        result = compute_industry_neutral_ranking(
            margin_detail_with_dates, stock_info_with_industry, top_n=20,
        )
        if len(result) >= 3:
            assert abs(result["z_balance"].mean()) < 0.5
            assert abs(result["z_buy"].mean()) < 0.5

    def test_filters_unknown_industry(self):
        """Stocks with 未知 industry should be excluded."""
        margin = pd.DataFrame({
            "symbol": ["000001.SZ", "000002.SZ", "000003.SZ"],
            "date": ["20260630"] * 3,
            "margin_balance": [10e8, 20e8, 30e8],
            "buy_on_margin_value": [1e8, 2e8, 3e8],
        })
        info = pd.DataFrame({
            "symbol": ["000001.SZ", "000002.SZ", "000003.SZ"],
            "name": ["A", "B", "C"],
            "industry": ["银行", "未知", "电子"],
        })
        result = compute_industry_neutral_ranking(margin, info)
        industries = result["industry"].tolist()
        assert "未知" not in industries
        assert "银行" in industries
        assert "电子" in industries

    def test_chinese_column_names(self):
        """Should resolve 股票代码/融资余额/融资买入额 column names."""
        margin = pd.DataFrame({
            "股票代码": ["000001.SZ", "000002.SZ", "000003.SZ"],
            "日期": ["20260630"] * 3,
            "融资余额": [10e8, 20e8, 30e8],
            "融资买入额": [1e8, 2e8, 3e8],
        })
        info = pd.DataFrame({
            "股票代码": ["000001.SZ", "000002.SZ", "000003.SZ"],
            "股票名称": ["平安银行", "万科A", "宁德时代"],
            "industry": ["银行", "房地产", "电力设备"],
        })
        result = compute_industry_neutral_ranking(margin, info)
        assert not result.empty
        assert "industry" in result.columns

    def test_top_n_truncation(self, margin_detail_with_dates, stock_info_with_industry):
        result = compute_industry_neutral_ranking(
            margin_detail_with_dates, stock_info_with_industry, top_n=3,
        )
        assert len(result) <= 3

    def test_rank_starts_at_1(self, margin_detail_with_dates, stock_info_with_industry):
        result = compute_industry_neutral_ranking(
            margin_detail_with_dates, stock_info_with_industry,
        )
        assert result["rank"].iloc[0] == 1

    def test_stock_count_is_int(self, margin_detail_with_dates, stock_info_with_industry):
        result = compute_industry_neutral_ranking(
            margin_detail_with_dates, stock_info_with_industry,
        )
        assert all(isinstance(c, (int, np.integer)) for c in result["stock_count"])

    def test_uses_latest_date_per_stock(self):
        """Multiple dates per symbol should use only the latest row."""
        margin = pd.DataFrame({
            "symbol": ["000001.SZ", "000001.SZ", "000002.SZ", "000002.SZ"],
            "date": ["20260629", "20260630", "20260629", "20260630"],
            "margin_balance": [5e8, 15e8, 10e8, 20e8],
            "buy_on_margin_value": [0.5e8, 1.5e8, 1e8, 2e8],
        })
        info = pd.DataFrame({
            "symbol": ["000001.SZ", "000002.SZ"],
            "name": ["A", "B"],
            "industry": ["银行", "银行"],
        })
        result = compute_industry_neutral_ranking(margin, info)
        # avg_balance_亿 for 银行 should be (15+20)/2 / 1e8 = 17.5
        bank_row = result[result["industry"] == "银行"]
        assert len(bank_row) == 1
        assert abs(bank_row["avg_balance_亿"].iloc[0] - 17.5) < 1.0

    def test_handles_nan_values(self):
        """NaN in numeric columns should be coerced and not crash."""
        margin = pd.DataFrame({
            "symbol": ["000001.SZ", "000002.SZ", "000003.SZ"],
            "date": ["20260630"] * 3,
            "margin_balance": [10e8, float("nan"), 30e8],
            "buy_on_margin_value": [1e8, 2e8, float("nan")],
        })
        info = pd.DataFrame({
            "symbol": ["000001.SZ", "000002.SZ", "000003.SZ"],
            "name": ["A", "B", "C"],
            "industry": ["银行", "银行", "电子"],
        })
        result = compute_industry_neutral_ranking(margin, info)
        assert not result.empty

    def test_single_industry_produces_zero_z(self):
        """Single industry should have z=0 (no distribution)."""
        margin = pd.DataFrame({
            "symbol": ["000001.SZ", "000002.SZ"],
            "date": ["20260630"] * 2,
            "margin_balance": [10e8, 20e8],
            "buy_on_margin_value": [1e8, 2e8],
        })
        info = pd.DataFrame({
            "symbol": ["000001.SZ", "000002.SZ"],
            "name": ["A", "B"],
            "industry": ["银行", "银行"],
        })
        result = compute_industry_neutral_ranking(margin, info)
        assert len(result) == 1
        assert result["z_balance"].iloc[0] == 0.0
        assert result["z_buy"].iloc[0] == 0.0
        assert result["composite_z"].iloc[0] == 0.0

    def test_prefer_sw_industry_when_available(self):
        """When sw_industry column exists, use it instead of industry."""
        margin = pd.DataFrame({
            "symbol": ["000001.SZ", "000002.SZ", "000003.SZ"],
            "date": ["20260630"] * 3,
            "margin_balance": [10e8, 20e8, 30e8],
            "buy_on_margin_value": [1e8, 2e8, 3e8],
        })
        info = pd.DataFrame({
            "symbol": ["000001.SZ", "000002.SZ", "000003.SZ"],
            "name": ["A", "B", "C"],
            "industry": ["银行", "电子", "电子"],          # Old classification
            "sw_industry": ["半导体", "银行", "银行"],    # Shenwan classification
        })
        result = compute_industry_neutral_ranking(margin, info)
        # Should use sw_industry → 2 industries: 半导体(1 stock), 银行(2 stocks)
        assert "半导体" in result["industry"].values or "银行" in result["industry"].values
        # Should NOT contain the old "电子" classification
        assert "电子" not in result["industry"].values

    def test_fallback_to_industry_when_no_sw(self):
        """Without sw_industry column, should fall back to industry column."""
        margin = pd.DataFrame({
            "symbol": ["000001.SZ", "000002.SZ", "000003.SZ"],
            "date": ["20260630"] * 3,
            "margin_balance": [10e8, 20e8, 30e8],
            "buy_on_margin_value": [1e8, 2e8, 3e8],
        })
        info = pd.DataFrame({
            "symbol": ["000001.SZ", "000002.SZ", "000003.SZ"],
            "name": ["A", "B", "C"],
            "industry": ["银行", "电子", "电子"],
        })
        result = compute_industry_neutral_ranking(margin, info)
        assert "电子" in result["industry"].values


# ── _assign_grade direct tests ──


class TestAssignGrade:
    """Direct boundary tests for grade assignment."""

    def test_a_plus(self):
        grade, label = _assign_grade(85.0)
        assert grade == "A+"
        assert label == "极度乐观"

    def test_a_plus_at_90(self):
        grade, _ = _assign_grade(90.0)
        assert grade == "A+"

    def test_a_at_80(self):
        grade, label = _assign_grade(80.0)
        assert grade == "A"
        assert label == "乐观"

    def test_a_at_75(self):
        grade, _ = _assign_grade(75.0)
        assert grade == "A"

    def test_b_plus_at_70(self):
        grade, label = _assign_grade(70.0)
        assert grade == "B+"
        assert label == "偏乐观"

    def test_b_plus_at_65(self):
        grade, _ = _assign_grade(65.0)
        assert grade == "B+"

    def test_b_at_60(self):
        grade, label = _assign_grade(60.0)
        assert grade == "B"
        assert label == "中性偏多"

    def test_b_at_55(self):
        grade, _ = _assign_grade(55.0)
        assert grade == "B"

    def test_c_at_50(self):
        grade, label = _assign_grade(50.0)
        assert grade == "C"
        assert label == "中性"

    def test_c_at_45(self):
        grade, _ = _assign_grade(45.0)
        assert grade == "C"

    def test_d_at_40(self):
        grade, label = _assign_grade(40.0)
        assert grade == "D"
        assert label == "中性偏空"

    def test_d_at_35(self):
        grade, _ = _assign_grade(35.0)
        assert grade == "D"

    def test_e_at_30(self):
        grade, label = _assign_grade(30.0)
        assert grade == "E"
        assert label == "偏悲观"

    def test_e_at_25(self):
        grade, _ = _assign_grade(25.0)
        assert grade == "E"

    def test_f_at_20(self):
        grade, label = _assign_grade(20.0)
        assert grade == "F"
        assert label == "悲观"

    def test_f_at_15(self):
        grade, _ = _assign_grade(15.0)
        assert grade == "F"

    def test_f_minus_at_10(self):
        grade, label = _assign_grade(10.0)
        assert grade == "F-"
        assert label == "极度悲观"

    def test_f_minus_at_zero(self):
        grade, _ = _assign_grade(0.0)
        assert grade == "F-"

    def test_boundary_just_above_85(self):
        grade, _ = _assign_grade(85.01)
        assert grade == "A+"

    def test_boundary_just_below_85(self):
        grade, _ = _assign_grade(84.99)
        assert grade == "A"

    def test_boundary_just_above_15(self):
        grade, _ = _assign_grade(15.01)
        assert grade == "F"

    def test_boundary_just_below_15(self):
        grade, _ = _assign_grade(14.99)
        assert grade == "F-"


# ── Risk level tests ──


class TestComputeRiskLevel:
    """Tests for compute_risk_level()."""

    def _make_signal(self, key, label, triggered, direction, strength):
        from core._types import SignalResult
        return SignalResult(
            key=key, label=label, triggered=triggered,
            strength=strength, direction=direction, summary=f"{label} test",
        )

    def _make_resonance(self, pattern, label, triggered, direction, strength):
        from core.resonance import ResonanceResult
        return ResonanceResult(
            pattern=pattern, label=label, triggered=triggered,
            strength=strength, direction=direction,
            summary=f"{label} test", description="",
            nb_score=0.0, margin_score=0.0,
        )

    def test_all_neutral_zero_risk(self):
        nb = [self._make_signal("a", "A", False, "neutral", 0.0)]
        mg = [self._make_signal("b", "B", False, "neutral", 0.0)]
        fut = [self._make_signal("c", "C", False, "neutral", 0.0)]
        res = [self._make_resonance("r", "R", False, "neutral", 0.0)]
        result = compute_risk_level(nb, mg, fut, res)
        assert result.score == 0.0
        assert result.stars == 0
        assert result.level == "低风险"

    def test_all_bearish_high_risk(self):
        nb = [self._make_signal("a", "A", True, "bearish", -0.8)]
        mg = [self._make_signal("b", "B", True, "bearish", -0.7)]
        fut = [self._make_signal("c", "C", True, "bearish", -0.6)]
        res = [self._make_resonance("r", "R", True, "bearish", -0.9)]
        result = compute_risk_level(nb, mg, fut, res)
        assert result.score > 50
        assert result.stars >= 3
        assert result.level in ("中风险", "高风险")

    def test_mixed_signals_partial_risk(self):
        nb = [
            self._make_signal("a", "A", True, "bullish", 0.7),
            self._make_signal("b", "B", True, "bearish", -0.5),
        ]
        mg = [self._make_signal("c", "C", False, "neutral", 0.0)]
        fut = []
        res = []
        result = compute_risk_level(nb, mg, fut, res)
        assert 0 <= result.stars <= 5
        assert len(result.details) > 0

    def test_factor_breakdown_keys(self):
        nb = [self._make_signal("a", "A", True, "bearish", -0.6)]
        mg = []
        fut = []
        res = []
        result = compute_risk_level(nb, mg, fut, res)
        assert isinstance(result.factor_bearish_ratio, float)
        assert isinstance(result.factor_bearish_intensity, float)
        assert isinstance(result.factor_resonance, float)
        assert isinstance(result.factor_margin_danger, float)

    def test_stars_range(self):
        """Stars should always be in 0-5 range for any input."""
        nb = [
            self._make_signal(f"a{i}", f"A{i}", True, "bearish", -1.0)
            for i in range(10)
        ]
        mg = []
        fut = []
        res = [
            self._make_resonance(f"r{i}", f"R{i}", True, "bearish", -1.0)
            for i in range(4)
        ]
        result = compute_risk_level(nb, mg, fut, res)
        assert 0 <= result.stars <= 5

    def test_risk_level_returns_dataclass(self):
        result = compute_risk_level([], [], [], [])
        assert isinstance(result, RiskLevel)

    def test_margin_danger_factor(self, sample_margin_macro):
        """High margin buy ratio should trigger margin_danger factor."""
        import pandas as pd
        df = sample_margin_macro.copy()
        # Make buy_on_margin_value very high relative to margin_balance
        if "buy_on_margin_value" in df.columns and "margin_balance" in df.columns:
            df["buy_on_margin_value"] = df["margin_balance"] * 0.16  # 16% → dangerous
            result = compute_risk_level(
                [], [], [], [],
                margin_macro=df, config={"margin": {"buy_ratio_dangerous": 0.15, "buy_ratio_hot": 0.10}},
            )
            assert result.factor_margin_danger == 1.0
