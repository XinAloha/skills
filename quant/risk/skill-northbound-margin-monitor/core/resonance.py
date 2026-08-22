"""Cross-signal resonance / divergence detection.

Analyses northbound and margin signals jointly to identify:
  - Bullish resonance:   northbound inflow + margin expansion
  - Bearish resonance:   northbound outflow + margin contraction
  - Cautious divergence: northbound inflow + margin deleveraging (smart money vs retail)
  - Dangerous divergence:northbound outflow + margin leveraging (foreign exits, retail leverages)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class ResonanceResult:
    """Output from resonance/divergence analysis."""
    pattern: str           # "bullish_resonance", "bearish_resonance", etc.
    label: str             # Chinese label
    triggered: bool
    strength: float        # -1.0 to 1.0
    direction: str         # "bullish", "bearish", "neutral"
    summary: str
    description: str       # longer explanation
    nb_score: float        # northbound composite score
    margin_score: float    # margin composite score


# ------------------------------------------------------------------
# Pattern definitions
# ------------------------------------------------------------------

def detect_bullish_resonance(
    nb_score: float,
    margin_score: float,
    nb_bullish_count: int,
    margin_bullish_count: int,
    config: dict,
) -> ResonanceResult:
    """Northbound inflow + margin expansion → strong bullish.

    Both foreign capital and domestic margin are flowing in.
    This is the strongest bullish signal.
    """
    enable = config.get("resonance", {}).get("enable_resonance", True)
    if not enable:
        return ResonanceResult(
            pattern="bullish_resonance", label="偏多共振",
            triggered=False, strength=0.0, direction="neutral",
            summary="共振检测未启用",
            description="", nb_score=nb_score, margin_score=margin_score,
        )

    # Both scores positive = resonance
    triggered = nb_score > 0.1 and margin_score > 0.1
    strength = min(nb_score, margin_score) if triggered else 0.0

    if triggered:
        if nb_score > 0.5 and margin_score > 0.5:
            summary = "强偏多共振：北向资金+融资双双大幅流入，市场做多共识强烈"
            strength = min(strength * 1.5, 1.0)
        elif nb_score > 0.3 and margin_score > 0.3:
            summary = "偏多共振：北向资金与融资同步流入，做多信号明确"
        else:
            summary = "弱偏多共振：北向与融资均偏正向，但幅度有限"

        return ResonanceResult(
            pattern="bullish_resonance", label="偏多共振",
            triggered=True, strength=round(strength, 4), direction="bullish",
            summary=summary,
            description=(
                f"北向得分{nb_score:.2f}（{nb_bullish_count}个看多信号），"
                f"融资得分{margin_score:.2f}（{margin_bullish_count}个看多信号）。"
                f"外资与杠杆资金同步做多，短期上涨概率较高。"
            ),
            nb_score=nb_score, margin_score=margin_score,
        )

    return ResonanceResult(
        pattern="bullish_resonance", label="偏多共振",
        triggered=False, strength=0.0, direction="neutral",
        summary="无偏多共振信号",
        description=f"北向{nb_score:.2f}，融资{margin_score:.2f}，未形成做多共振",
        nb_score=nb_score, margin_score=margin_score,
    )


def detect_bearish_resonance(
    nb_score: float,
    margin_score: float,
    nb_bearish_count: int,
    margin_bearish_count: int,
    config: dict,
) -> ResonanceResult:
    """Northbound outflow + margin contraction → strong bearish.

    Both foreign capital and domestic margin are exiting.
    This is the strongest bearish signal.
    """
    enable = config.get("resonance", {}).get("enable_resonance", True)
    if not enable:
        return ResonanceResult(
            pattern="bearish_resonance", label="偏空共振",
            triggered=False, strength=0.0, direction="neutral",
            summary="共振检测未启用",
            description="", nb_score=nb_score, margin_score=margin_score,
        )

    triggered = nb_score < -0.1 and margin_score < -0.1
    strength = max(nb_score, margin_score) if triggered else 0.0

    if triggered:
        if nb_score < -0.5 and margin_score < -0.5:
            summary = "强偏空共振：北向资金+融资双双大幅流出，市场做空共识强烈"
            strength = max(strength * 1.5, -1.0)
        elif nb_score < -0.3 and margin_score < -0.3:
            summary = "偏空共振：北向资金与融资同步流出，做空信号明确"
        else:
            summary = "弱偏空共振：北向与融资均偏负向，但幅度有限"

        return ResonanceResult(
            pattern="bearish_resonance", label="偏空共振",
            triggered=True, strength=round(strength, 4), direction="bearish",
            summary=summary,
            description=(
                f"北向得分{nb_score:.2f}（{nb_bearish_count}个看空信号），"
                f"融资得分{margin_score:.2f}（{margin_bearish_count}个看空信号）。"
                f"外资与杠杆资金同步撤离，短期下行风险加大。"
            ),
            nb_score=nb_score, margin_score=margin_score,
        )

    return ResonanceResult(
        pattern="bearish_resonance", label="偏空共振",
        triggered=False, strength=0.0, direction="neutral",
        summary="无偏空共振信号",
        description=f"北向{nb_score:.2f}，融资{margin_score:.2f}，未形成做空共振",
        nb_score=nb_score, margin_score=margin_score,
    )


def detect_cautious_divergence(
    nb_score: float,
    margin_score: float,
    config: dict,
) -> ResonanceResult:
    """Northbound inflow + margin deleveraging → cautious bullish.

    Smart money (foreign) buying while retail (margin) is reducing leverage.
    This is a contrarian bullish signal — smart money accumulating at
    lower prices while retail capitulates.
    """
    enable = config.get("resonance", {}).get("enable_divergence", True)
    if not enable:
        return ResonanceResult(
            pattern="cautious_divergence", label="谨慎偏多",
            triggered=False, strength=0.0, direction="neutral",
            summary="背离检测未启用",
            description="", nb_score=nb_score, margin_score=margin_score,
        )

    # Northbound positive, margin negative → smart money in, retail out
    triggered = nb_score > 0.2 and margin_score < -0.1

    if triggered:
        strength = nb_score * 0.7  # Bullish but tempered
        summary = "谨慎偏多：北向资金流入但融资去杠杆，聪明钱进场、散户离场"
        return ResonanceResult(
            pattern="cautious_divergence", label="谨慎偏多",
            triggered=True, strength=round(strength, 4), direction="bullish",
            summary=summary,
            description=(
                f"北向得分{nb_score:.2f}（外资流入），融资得分{margin_score:.2f}（去杠杆）。"
                f"聪明钱在散户恐慌时逆势加仓，历史上常是中期底部信号。"
                f"但需确认北向流入非短期对冲行为。"
            ),
            nb_score=nb_score, margin_score=margin_score,
        )

    return ResonanceResult(
        pattern="cautious_divergence", label="谨慎偏多",
        triggered=False, strength=0.0, direction="neutral",
        summary="无谨慎偏多信号",
        description=f"北向{nb_score:.2f}，融资{margin_score:.2f}，未形成谨慎偏多背离",
        nb_score=nb_score, margin_score=margin_score,
    )


def detect_dangerous_divergence(
    nb_score: float,
    margin_score: float,
    config: dict,
) -> ResonanceResult:
    """Northbound outflow + margin leveraging → dangerous divergence.

    Foreign capital exiting while retail increases leverage.
    This is the most dangerous signal — smart money selling into
    retail buying, typical of distribution/ topping patterns.
    """
    enable = config.get("resonance", {}).get("enable_divergence", True)
    if not enable:
        return ResonanceResult(
            pattern="dangerous_divergence", label="背离危险",
            triggered=False, strength=0.0, direction="neutral",
            summary="背离检测未启用",
            description="", nb_score=nb_score, margin_score=margin_score,
        )

    # Northbound negative, margin positive → foreign exits, retail leverages
    triggered = nb_score < -0.2 and margin_score > 0.1

    if triggered:
        strength = nb_score * 0.8  # Bearish, amplified
        summary = "背离危险：北向资金流出但融资加杠杆，外资撤离、散户接盘"
        return ResonanceResult(
            pattern="dangerous_divergence", label="背离危险",
            triggered=True, strength=round(strength, 4), direction="bearish",
            summary=summary,
            description=(
                f"北向得分{nb_score:.2f}（外资流出），融资得分{margin_score:.2f}（加杠杆）。"
                f"外资在散户加杠杆时撤离，这是典型的顶部派发信号。"
                f"历史上此类背离后市场调整概率显著增高，需高度警惕。"
            ),
            nb_score=nb_score, margin_score=margin_score,
        )

    return ResonanceResult(
        pattern="dangerous_divergence", label="背离危险",
        triggered=False, strength=0.0, direction="neutral",
        summary="无背离危险信号",
        description=f"北向{nb_score:.2f}，融资{margin_score:.2f}，未形成危险背离",
        nb_score=nb_score, margin_score=margin_score,
    )


# ------------------------------------------------------------------
# Orchestrator
# ------------------------------------------------------------------

def analyse_resonance(
    nb_composite: float,
    margin_composite: float,
    nb_bullish_count: int,
    nb_bearish_count: int,
    margin_bullish_count: int,
    margin_bearish_count: int,
    config: dict,
) -> list[ResonanceResult]:
    """Run all 4 resonance/divergence pattern detectors.

    Args:
        nb_composite: Northbound composite score (-1 to 1).
        margin_composite: Margin composite score (-1 to 1).
        nb_bullish_count: Number of bullish northbound signals.
        nb_bearish_count: Number of bearish northbound signals.
        margin_bullish_count: Number of bullish margin signals.
        margin_bearish_count: Number of bearish margin signals.
        config: Full runtime config dict.

    Returns:
        List of 4 ResonanceResult objects.
    """
    return [
        detect_bullish_resonance(
            nb_composite, margin_composite,
            nb_bullish_count, margin_bullish_count, config,
        ),
        detect_bearish_resonance(
            nb_composite, margin_composite,
            nb_bearish_count, margin_bearish_count, config,
        ),
        detect_cautious_divergence(
            nb_composite, margin_composite, config,
        ),
        detect_dangerous_divergence(
            nb_composite, margin_composite, config,
        ),
    ]


def get_triggered_patterns(results: list[ResonanceResult]) -> list[ResonanceResult]:
    """Return only triggered resonance/divergence patterns."""
    return [r for r in results if r.triggered]


def get_primary_signal(results: list[ResonanceResult]) -> Optional[ResonanceResult]:
    """Return the strongest triggered resonance/divergence pattern.

    Preference order: dangerous_divergence > bearish_resonance >
    bullish_resonance > cautious_divergence.
    Within each, stronger strength wins.
    """
    triggered = get_triggered_patterns(results)
    if not triggered:
        return None

    # Priority: risk signals first
    priority = {
        "dangerous_divergence": 4,
        "bearish_resonance": 3,
        "bullish_resonance": 2,
        "cautious_divergence": 1,
    }
    return max(triggered, key=lambda r: (priority.get(r.pattern, 0), abs(r.strength)))


def compute_resonance_score(results: list[ResonanceResult], config: dict | None = None) -> float:
    """Compute overall resonance score from all 4 patterns.

    Args:
        results: List of ResonanceResult from analyse_resonance().
        config: Runtime config dict for custom pattern weights.

    Returns:
        Float in range -1.0 to 1.0.
    """
    if not results:
        return 0.0

    default_weights = {
        "bullish_resonance": 1.0,
        "bearish_resonance": 1.0,
        "cautious_divergence": 0.5,
        "dangerous_divergence": 0.8,
    }
    weights = (config or {}).get("resonance", {}).get("pattern_weights", default_weights)

    total = 0.0
    weight_sum = 0.0
    for r in results:
        w = weights.get(r.pattern, 0.5)
        total += r.strength * w
        weight_sum += w

    if weight_sum == 0:
        return 0.0
    return round(total / weight_sum, 4)
