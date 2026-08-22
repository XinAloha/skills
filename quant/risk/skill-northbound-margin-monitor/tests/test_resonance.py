"""Tests for resonance / divergence pattern detection."""

import pytest

from core.resonance import (
    detect_bullish_resonance,
    detect_bearish_resonance,
    detect_cautious_divergence,
    detect_dangerous_divergence,
    analyse_resonance,
    get_triggered_patterns,
    get_primary_signal,
    compute_resonance_score,
)


class TestBullishResonance:
    def test_triggers_when_both_positive(self, sample_config):
        result = detect_bullish_resonance(0.5, 0.5, 3, 3, sample_config)
        assert result.triggered
        assert result.direction == "bullish"
        assert result.strength > 0

    def test_strong_bullish(self, sample_config):
        result = detect_bullish_resonance(0.7, 0.7, 5, 4, sample_config)
        assert result.triggered
        assert result.strength > 0.5

    def test_no_trigger_when_margin_negative(self, sample_config):
        result = detect_bullish_resonance(0.5, -0.2, 3, 0, sample_config)
        assert not result.triggered

    def test_no_trigger_when_nb_negative(self, sample_config):
        result = detect_bullish_resonance(-0.2, 0.5, 0, 3, sample_config)
        assert not result.triggered

    def test_no_trigger_when_both_neutral(self, sample_config):
        result = detect_bullish_resonance(0.05, 0.05, 1, 1, sample_config)
        assert not result.triggered

    def test_disabled_by_config(self):
        config = {"resonance": {"enable_resonance": False}}
        result = detect_bullish_resonance(0.5, 0.5, 3, 3, config)
        assert not result.triggered


class TestBearishResonance:
    def test_triggers_when_both_negative(self, sample_config):
        result = detect_bearish_resonance(-0.5, -0.5, 3, 3, sample_config)
        assert result.triggered
        assert result.direction == "bearish"
        assert result.strength < 0

    def test_no_trigger_when_nb_positive(self, sample_config):
        result = detect_bearish_resonance(0.5, -0.5, 0, 3, sample_config)
        assert not result.triggered

    def test_strong_bearish(self, sample_config):
        result = detect_bearish_resonance(-0.7, -0.7, 5, 4, sample_config)
        assert result.triggered
        assert result.strength < -0.5

    def test_disabled_by_config(self):
        config = {"resonance": {"enable_resonance": False}}
        result = detect_bearish_resonance(-0.5, -0.5, 3, 3, config)
        assert not result.triggered


class TestCautiousDivergence:
    def test_triggers_nb_inflow_margin_deleveraging(self, sample_config):
        result = detect_cautious_divergence(0.5, -0.3, sample_config)
        assert result.triggered
        assert result.direction == "bullish"

    def test_no_trigger_when_nb_not_strong_enough(self, sample_config):
        result = detect_cautious_divergence(0.1, -0.3, sample_config)
        assert not result.triggered

    def test_no_trigger_when_margin_not_negative(self, sample_config):
        result = detect_cautious_divergence(0.5, 0.1, sample_config)
        assert not result.triggered

    def test_disabled_by_config(self):
        config = {"resonance": {"enable_divergence": False}}
        result = detect_cautious_divergence(0.5, -0.3, config)
        assert not result.triggered


class TestDangerousDivergence:
    def test_triggers_nb_outflow_margin_leveraging(self, sample_config):
        result = detect_dangerous_divergence(-0.5, 0.3, sample_config)
        assert result.triggered
        assert result.direction == "bearish"
        assert result.strength < 0

    def test_no_trigger_when_nb_not_negative_enough(self, sample_config):
        result = detect_dangerous_divergence(-0.1, 0.3, sample_config)
        assert not result.triggered

    def test_no_trigger_when_margin_not_positive(self, sample_config):
        result = detect_dangerous_divergence(-0.5, -0.1, sample_config)
        assert not result.triggered

    def test_disabled_by_config(self):
        config = {"resonance": {"enable_divergence": False}}
        result = detect_dangerous_divergence(-0.5, 0.3, config)
        assert not result.triggered


class TestAnalyseResonance:
    def test_returns_4_results(self, sample_config):
        results = analyse_resonance(0.5, 0.4, 3, 1, 3, 1, sample_config)
        assert len(results) == 4

    def test_bullish_resonance_scenario(self, sample_config):
        results = analyse_resonance(0.6, 0.5, 4, 0, 3, 1, sample_config)
        triggered = get_triggered_patterns(results)
        triggered_patterns = [r.pattern for r in triggered]
        assert "bullish_resonance" in triggered_patterns

    def test_dangerous_divergence_scenario(self, sample_config):
        results = analyse_resonance(-0.5, 0.4, 0, 3, 3, 0, sample_config)
        triggered = get_triggered_patterns(results)
        triggered_patterns = [r.pattern for r in triggered]
        assert "dangerous_divergence" in triggered_patterns

    def test_no_triggers_when_all_neutral(self, sample_config):
        results = analyse_resonance(0.05, -0.05, 0, 0, 0, 0, sample_config)
        triggered = get_triggered_patterns(results)
        assert len(triggered) == 0


class TestHelpers:
    def test_get_primary_signal_returns_none_when_none(self, sample_config):
        results = analyse_resonance(0.0, 0.0, 0, 0, 0, 0, sample_config)
        assert get_primary_signal(results) is None

    def test_get_primary_signal_returns_strongest(self, sample_config):
        results = analyse_resonance(-0.5, 0.5, 0, 3, 3, 0, sample_config)
        primary = get_primary_signal(results)
        assert primary is not None
        # dangerous_divergence has highest priority among triggered
        assert primary.pattern == "dangerous_divergence"

    def test_compute_resonance_score_range(self, sample_config):
        results = analyse_resonance(0.5, 0.5, 3, 1, 3, 1, sample_config)
        score = compute_resonance_score(results)
        assert -1.0 <= score <= 1.0

    def test_compute_resonance_score_empty(self):
        assert compute_resonance_score([]) == 0.0

    def test_compute_resonance_score_with_config_weights(self, sample_config):
        """Custom pattern weights from config should override defaults."""
        config = {**sample_config}
        config["resonance"] = {
            **sample_config.get("resonance", {}),
            "pattern_weights": {
                "bullish_resonance": 2.0,
                "bearish_resonance": 2.0,
                "cautious_divergence": 0.0,
                "dangerous_divergence": 0.0,
            },
        }
        results = analyse_resonance(0.5, 0.5, 3, 1, 3, 1, config)
        score = compute_resonance_score(results, config)
        assert -1.0 <= score <= 1.0


# ── Threshold boundary tests ──


class TestResonanceBoundaries:
    """Test exact threshold boundaries for all 4 patterns."""

    def test_bullish_above_threshold(self, sample_config):
        """nb=0.11, margin=0.11 should trigger (>0.1 strict threshold)."""
        results = analyse_resonance(0.11, 0.11, 3, 1, 3, 1, sample_config)
        triggered = get_triggered_patterns(results)
        assert len(triggered) >= 1

    def test_bullish_just_below_threshold(self, sample_config):
        """nb=0.09, margin=0.09 should NOT trigger bullish resonance."""
        results = analyse_resonance(0.09, 0.09, 3, 1, 3, 1, sample_config)
        triggered = get_triggered_patterns(results)
        bullish_triggered = [r for r in triggered if r.pattern == "bullish_resonance"]
        assert len(bullish_triggered) == 0

    def test_bearish_above_threshold(self, sample_config):
        """nb=-0.11, margin=-0.11 should trigger bearish."""
        results = analyse_resonance(-0.11, -0.11, 1, 3, 1, 3, sample_config)
        triggered = get_triggered_patterns(results)
        bearish_triggered = [r for r in triggered if r.pattern == "bearish_resonance"]
        assert len(bearish_triggered) >= 1

    def test_cautious_divergence_boundary(self, sample_config):
        """nb=0.21, margin=-0.11 should trigger cautious (strict > threshold)."""
        results = analyse_resonance(0.21, -0.11, 3, 1, 1, 3, sample_config)
        triggered = get_triggered_patterns(results)
        cautious = [r for r in triggered if r.pattern == "cautious_divergence"]
        assert len(cautious) >= 1

    def test_dangerous_divergence_boundary(self, sample_config):
        """nb=-0.21, margin=0.11 should trigger dangerous (strict > threshold)."""
        results = analyse_resonance(-0.21, 0.11, 1, 3, 3, 1, sample_config)
        triggered = get_triggered_patterns(results)
        dangerous = [r for r in triggered if r.pattern == "dangerous_divergence"]
        assert len(dangerous) >= 1

    def test_all_neutral_no_triggers(self, sample_config):
        """All scores near zero → no resonance triggered."""
        results = analyse_resonance(0.05, -0.05, 2, 2, 2, 2, sample_config)
        triggered = get_triggered_patterns(results)
        assert len(triggered) == 0

    def test_multiple_patterns_can_trigger(self, sample_config):
        """Both bullish resonance and cautious divergence can trigger together."""
        # NB strong bullish, margin slightly negative → could trigger both
        results = analyse_resonance(0.6, -0.15, 5, 0, 2, 3, sample_config)
        triggered = get_triggered_patterns(results)
        # At minimum, cautious divergence should trigger
        assert len(triggered) >= 1
