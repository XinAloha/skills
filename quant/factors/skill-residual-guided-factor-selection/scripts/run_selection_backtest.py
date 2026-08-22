#!/usr/bin/env python3
"""Export frozen signals for $factor-backtest, with optional direct CLI fallback."""

from __future__ import annotations

from residual_factor_selection.backtest_adapter import main


if __name__ == "__main__":
    raise SystemExit(main())
