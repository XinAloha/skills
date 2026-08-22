"""Tests for llm/analyst.py — prompt building, fallback generation, API key resolution."""

import sys
from unittest.mock import MagicMock, patch

import pytest

from core._types import SignalResult
from core.resonance import ResonanceResult
from llm.analyst import (
    LLMAnalyst,
    _generate_fallback,
    build_panorama_prompt,
)


# ── Shared test data ──

def _make_signal(key, label, triggered, strength, direction, summary):
    return SignalResult(
        key=key, label=label, triggered=triggered,
        strength=strength, direction=direction, summary=summary,
    )


def _make_resonance(pattern, label, triggered, direction, summary, strength=0.0,
                    nb_score=0.0, margin_score=0.0):
    return ResonanceResult(
        pattern=pattern, label=label, triggered=triggered,
        strength=strength, direction=direction, summary=summary,
        description=summary, nb_score=nb_score, margin_score=margin_score,
    )


@pytest.fixture
def nb_signals():
    return [
        _make_signal("flow_trend", "净流向趋势", False, -0.33, "bearish", "净流出1日"),
        _make_signal("single_day_anomaly", "单日异常", False, -0.24, "bearish", "单日正常"),
        _make_signal("sector_preference", "板块偏好", False, 0.0, "bearish", "北向流出"),
        _make_signal("holdings_change", "重仓股变动", False, 0.0, "bearish", "变化不大"),
        _make_signal("cumulative_trend", "累计趋势", True, -0.10, "bearish", "加速流出"),
        _make_signal("market_flow_direction", "市场流向", True, 0.80, "bullish", "双双流入"),
    ]


@pytest.fixture
def margin_signals():
    return [
        _make_signal("margin_balance_trend", "融资余额趋势", True, 0.30, "bullish", "温和上升"),
        _make_signal("margin_buy_ratio", "融资买入比", True, -0.80, "bearish", "过度杠杆"),
        _make_signal("margin_heavy_stocks", "融资重仓股", True, 0.0, "neutral", "分散"),
        _make_signal("margin_type_dist", "融资类型分布", True, 0.0, "neutral", "各半"),
        _make_signal("short_trend", "融券趋势", False, -0.10, "bearish", "微增"),
        _make_signal("margin_short_ratio", "融资融券比", True, -0.30, "bearish", "偏空上升"),
    ]


@pytest.fixture
def resonance_results():
    return [
        _make_resonance("bullish_resonance", "偏多共振", False, "neutral", "无共振"),
        _make_resonance("bearish_resonance", "偏空共振", False, "neutral", "无共振"),
        _make_resonance("smart_money", "谨慎偏多", False, "neutral", "无背离"),
        _make_resonance("danger_divergence", "背离危险", False, "neutral", "无背离"),
    ]


# ── Helper: inject mock anthropic into sys.modules ──

def _inject_mock_anthropic(create_side_effect=None, create_return=None):
    """Inject a mock ``anthropic`` module into sys.modules so lazy import works."""
    mock_anthro_module = MagicMock()
    mock_client = MagicMock()
    if create_side_effect:
        mock_client.messages.create.side_effect = create_side_effect
    if create_return:
        mock_client.messages.create.return_value = create_return
    mock_anthro_module.Anthropic.return_value = mock_client
    sys.modules["anthropic"] = mock_anthro_module
    return mock_anthro_module, mock_client


def _remove_mock_anthropic():
    sys.modules.pop("anthropic", None)


# ── build_panorama_prompt tests ──

class TestBuildPanoramaPrompt:
    """Prompt building from panorama signal data."""

    def test_builds_prompt_smoke(self, nb_signals, margin_signals, resonance_results):
        prompt = build_panorama_prompt(
            composite_score=45.0,
            composite_grade="D",
            composite_label="中性偏空",
            composite_summary="资金面中性偏空",
            nb_signals=nb_signals,
            margin_signals=margin_signals,
            resonance_results=resonance_results,
            margin_balance_亿=29878,
            short_balance_亿=233,
            margin_buy_亿=3346,
            top_industries=["信息技术", "工业", "原材料"],
        )
        assert "45" in prompt
        assert "中性偏空" in prompt
        assert "净流向趋势" in prompt
        assert "融资余额趋势" in prompt
        assert "29878" in prompt
        assert "233" in prompt
        assert "3346" in prompt
        assert "信息技术" in prompt

    def test_empty_signals(self):
        prompt = build_panorama_prompt(
            composite_score=50.0,
            composite_grade="C",
            composite_label="中性",
            composite_summary="中性",
            nb_signals=[],
            margin_signals=[],
            resonance_results=[],
        )
        assert "无北向数据" in prompt
        assert "无融资融券数据" in prompt
        assert "无共振/背离信号" in prompt

    def test_empty_top_industries(self, nb_signals, margin_signals, resonance_results):
        prompt = build_panorama_prompt(
            composite_score=50.0,
            composite_grade="C",
            composite_label="中性",
            composite_summary="中性",
            nb_signals=nb_signals,
            margin_signals=margin_signals,
            resonance_results=resonance_results,
            top_industries=None,
        )
        assert "数据不可用" in prompt

    def test_top_industries_truncated(self, nb_signals, margin_signals, resonance_results):
        industries = ["A", "B", "C", "D", "E", "F", "G"]
        prompt = build_panorama_prompt(
            composite_score=50.0,
            composite_grade="C",
            composite_label="中性",
            composite_summary="中性",
            nb_signals=nb_signals,
            margin_signals=margin_signals,
            resonance_results=resonance_results,
            top_industries=industries,
        )
        assert "A、B、C、D、E" in prompt
        assert "F" not in prompt


# ── _generate_fallback tests ──

class TestGenerateFallback:
    """Rule-based fallback generation for 4 regimes."""

    def test_aggressive_regime(self):
        text = _generate_fallback(70.0, "B", 4, 3, 1, 25000)
        assert "偏进攻" in text
        assert "B" in text
        assert "4/7" in text
        assert "3/7" in text

    def test_watchful_bullish_regime(self):
        text = _generate_fallback(55.0, "C+", 3, 2, 0, 20000)
        assert "观望偏多" in text

    def test_defensive_cautious_regime(self):
        text = _generate_fallback(35.0, "D", 2, 4, 1, 28000)
        assert "防御偏谨慎" in text

    def test_defensive_regime(self):
        text = _generate_fallback(20.0, "E", 1, 5, 2, 32000)
        assert "防御" in text
        assert "显著偏空" in text
        assert "处于历史高位" in text

    def test_no_triggered_signals(self):
        text = _generate_fallback(50.0, "C", 0, 0, 0, 10000)
        assert "无触发" in text

    def test_resonance_risk_included(self):
        text = _generate_fallback(40.0, "D", 3, 3, 2, 20000)
        assert "共振/背离信号触发" in text

    def test_all_zero_data(self):
        text = _generate_fallback(0.0, "F-", 0, 0, 0, 0)
        assert "防御" in text
        assert "F-" in text

    def test_short_line_advice(self):
        text = _generate_fallback(40.0, "D", 2, 3, 0, 15000)
        assert "短线" in text
        assert "中线" in text
        assert "长线" in text
        assert "规则引擎" in text

    def test_extracts_margin_buy_ratio(self):
        """Fallback should include precise margin buy ratio from signal detail."""
        mg = [
            _make_signal("margin_buy_ratio", "融资买入比", True, -0.8, "bearish",
                         "融资买入3346亿，估算买入比18%（≥15%）"),
        ]
        mg[0].detail = {"estimated_ratio": 0.18, "margin_buy_亿": 3346}
        text = _generate_fallback(45.0, "C", 2, 3, 0, 25000,
                                  margin_signals=mg)
        assert "18%" in text
        assert "警戒线" in text

    def test_extracts_futures_basis(self):
        """Fallback should include futures basis when provided."""
        fut = [
            _make_signal("futures_basis", "期货基差", True, -1.0, "bearish",
                         "期货贴水（-2.32%）"),
        ]
        fut[0].detail = {"avg_basis_pct": -2.32, "n_positive": 0, "n_total": 3}
        text = _generate_fallback(40.0, "D", 3, 3, 0, 25000,
                                  futures_signals=fut)
        assert "贴水" in text

    def test_extracts_flow_trend_consecutive_days(self):
        """Fallback should mention consecutive northbound flow days."""
        nb = [
            _make_signal("flow_trend", "净流向趋势", False, 0.67, "bullish",
                         "净流入2日"),
        ]
        nb[0].detail = {"consecutive_days": 2}
        text = _generate_fallback(50.0, "C", 1, 2, 0, 25000,
                                  nb_signals=nb)
        assert "2日" in text

    def test_extracts_resonance_labels(self):
        """Fallback should name triggered resonance patterns."""
        res = [
            _make_resonance("bearish_resonance", "偏空共振", True, "bearish",
                           "偏空共振触发", strength=-0.4),
        ]
        text = _generate_fallback(35.0, "D", 3, 4, 1, 25000,
                                  resonance_results=res)
        assert "偏空共振" in text

    def test_cross_validation_section_present(self):
        """Fallback should include a 三维交叉验证 section."""
        text = _generate_fallback(50.0, "C", 2, 3, 0, 25000)
        assert "三维交叉验证" in text

    def test_key_metrics_section_when_data_available(self):
        """Fallback should include 关键指标 when metrics are available."""
        mg = [
            _make_signal("margin_buy_ratio", "融资买入比", True, -0.8, "bearish", ""),
        ]
        mg[0].detail = {"estimated_ratio": 0.18}
        text = _generate_fallback(45.0, "C", 2, 3, 0, 25000,
                                  margin_signals=mg)
        assert "关键指标" in text

    def test_no_key_metrics_when_no_data(self):
        """Fallback should skip 关键指标 when no signal lists provided."""
        text = _generate_fallback(50.0, "C", 0, 0, 0, 10000)
        assert "关键指标" not in text


# ── LLMAnalyst tests ──

class TestLLMAnalystInit:
    """Model and config resolution."""

    def test_default_model(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_MODEL", raising=False)
        analyst = LLMAnalyst()
        assert analyst._model == "claude-sonnet-4-6"

    def test_model_from_env(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_MODEL", "deepseek-v4-pro")
        analyst = LLMAnalyst()
        assert analyst._model == "deepseek-v4-pro"

    def test_model_from_config(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_MODEL", raising=False)
        analyst = LLMAnalyst({"llm": {"model": "custom-model"}})
        assert analyst._model == "custom-model"

    def test_env_overrides_config(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_MODEL", "env-model")
        analyst = LLMAnalyst({"llm": {"model": "config-model"}})
        assert analyst._model == "env-model"

    def test_max_tokens_default(self):
        analyst = LLMAnalyst()
        assert analyst._max_tokens == 2048

    def test_max_tokens_from_config(self):
        analyst = LLMAnalyst({"llm": {"max_tokens": 2048}})
        assert analyst._max_tokens == 2048

    def test_base_url_from_env(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://api.deepseek.com/anthropic")
        analyst = LLMAnalyst()
        assert analyst._base_url == "https://api.deepseek.com/anthropic"

    def test_no_base_url_default(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_BASE_URL", raising=False)
        analyst = LLMAnalyst()
        assert analyst._base_url is None


class TestLLMAnalystAPIKey:
    """API key resolution order: env ANTHROPIC_API_KEY > ANTHROPIC_AUTH_TOKEN > config."""

    def test_key_from_anthropic_api_key(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-key1")
        monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
        _inject_mock_anthropic()
        try:
            analyst = LLMAnalyst()
            _ = analyst.client
            assert analyst._api_key == "sk-key1"
        finally:
            _remove_mock_anthropic()

    def test_key_from_auth_token(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "token-from-env")
        _inject_mock_anthropic()
        try:
            analyst = LLMAnalyst()
            _ = analyst.client
            assert analyst._api_key == "token-from-env"
        finally:
            _remove_mock_anthropic()

    def test_key_from_config(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
        _inject_mock_anthropic()
        try:
            analyst = LLMAnalyst({"llm": {"api_key": "config-key"}})
            _ = analyst.client
            assert analyst._api_key == "config-key"
        finally:
            _remove_mock_anthropic()

    def test_missing_key_raises(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
        analyst = LLMAnalyst()
        with pytest.raises(RuntimeError, match="API key not configured"):
            _ = analyst.client

    def test_placeholder_key_raises(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-xxx")
        analyst = LLMAnalyst()
        with pytest.raises(RuntimeError, match="API key not configured"):
            _ = analyst.client

    def test_client_cached(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-cached")
        _inject_mock_anthropic()
        try:
            analyst = LLMAnalyst()
            c1 = analyst.client
            c2 = analyst.client
            assert c1 is c2
        finally:
            _remove_mock_anthropic()


class TestLLMAnalystAnalyze:
    """analyze() method — fallback paths."""

    def _analyze_inputs(self):
        nb = [
            _make_signal("f1", "L1", True, 0.5, "bullish", "ok"),
            _make_signal("f2", "L2", False, -0.2, "bearish", "nope"),
        ]
        mg = [
            _make_signal("m1", "M1", True, -0.5, "bearish", "bad"),
        ]
        res = [
            _make_resonance("r1", "R1", True, "bullish", "共振!", 0.6),
        ]
        return nb, mg, res

    def test_fallback_when_no_api_key(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
        monkeypatch.delenv("ANTHROPIC_MODEL", raising=False)
        analyst = LLMAnalyst()
        nb, mg, res = self._analyze_inputs()
        text, source, model = analyst.analyze(
            50.0, "C", "中性", "中性", nb, mg, res,
        )
        assert source == "fallback"
        assert "观望偏多" in text
        assert model == "claude-sonnet-4-6"

    def test_fallback_on_api_error(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-will-fail")
        _inject_mock_anthropic(create_side_effect=Exception("Network error"))
        try:
            analyst = LLMAnalyst()
            nb, mg, res = self._analyze_inputs()
            text, source, model = analyst.analyze(
                70.0, "B", "偏多", "偏多", nb, mg, res,
            )
            assert source == "fallback"
            assert "偏进攻" in text
        finally:
            _remove_mock_anthropic()

    def test_fallback_on_empty_response(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-empty")
        mock_resp = MagicMock()
        mock_resp.content = []
        _inject_mock_anthropic(create_return=mock_resp)
        try:
            analyst = LLMAnalyst()
            nb, mg, res = self._analyze_inputs()
            text, source, model = analyst.analyze(
                40.0, "D", "偏空", "偏空", nb, mg, res,
            )
            assert source == "fallback"
        finally:
            _remove_mock_anthropic()

    def test_real_response(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-real")
        mock_block = MagicMock()
        mock_block.text = "AI generated analysis here"
        mock_resp = MagicMock()
        mock_resp.content = [mock_block]
        _inject_mock_anthropic(create_return=mock_resp)
        try:
            analyst = LLMAnalyst()
            nb, mg, res = self._analyze_inputs()
            text, source, model = analyst.analyze(
                55.0, "C+", "中性偏多", "中性偏多", nb, mg, res,
            )
            assert source == "real"
            assert "AI generated analysis here" == text
        finally:
            _remove_mock_anthropic()

    def test_trigger_counts_passed_to_fallback(self):
        nb = [
            _make_signal("a", "A", True, 0.5, "bullish", "x"),
            _make_signal("b", "B", True, 0.3, "bullish", "y"),
            _make_signal("c", "C", False, 0.0, "neutral", "z"),
        ]
        mg = [
            _make_signal("d", "D", True, -0.5, "bearish", "w"),
        ]
        text = _generate_fallback(45.0, "D", nb_triggered=2, mg_triggered=1,
                                  resonance_triggered=0, margin_balance_亿=15000)
        assert "2/7" in text
        assert "1/7" in text
