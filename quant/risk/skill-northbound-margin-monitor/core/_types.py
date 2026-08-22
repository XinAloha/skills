"""Shared types used across core modules."""

from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass
class SignalResult:
    """Output from a single signal detector."""
    key: str
    label: str
    triggered: bool
    strength: float       # -1.0 (strong bearish) to 1.0 (strong bullish)
    direction: str        # "bullish", "bearish", "neutral"
    summary: str
    detail: dict = field(default_factory=dict)


def neutral_signal(key: str, label: str, summary: str = "", detail: dict | None = None) -> SignalResult:
    """Create a neutral (non-triggered) SignalResult."""
    return SignalResult(
        key=key, label=label, triggered=False,
        strength=0.0, direction="neutral", summary=summary,
        detail=detail or {},
    )


def apply_signal_decay(signal: SignalResult, half_life_days: int = 30) -> float:
    """Apply exponential decay to signal strength based on persistence.

    Uses the signal's ``consecutive_days`` from its detail dict (defaults to 1
    if absent, meaning a fresh signal with no decay).

    Formula: ``decay_factor = 2^(-consecutive_days / half_life_days)``

    A signal that just triggered today has decay_factor ≈ 1.0.
    A signal that persisted for *half_life_days* days has decay_factor = 0.5.

    Args:
        signal: The SignalResult to decay.
        half_life_days: Days after which strength halves.

    Returns:
        Decayed strength value in the same sign as original strength.
    """
    if not signal.triggered or signal.strength == 0.0:
        return signal.strength

    consecutive = signal.detail.get("consecutive_days", 1)
    if consecutive <= 1 or half_life_days <= 0:
        return signal.strength

    decay_factor = math.pow(2, -consecutive / half_life_days)
    return signal.strength * decay_factor
