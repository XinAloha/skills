"""Alpha101 formula engine.

Implements the 101 alpha factors based on JoinQuant Alpha101 formulas.
Reference implementation source: JoinQuant official factor documentation and
JoinQuant factor-value API corrections used by the upstream local skill.

Usage::

    from alpha_runtime.alpha101_formulas import compute_all_alpha101

    results = compute_all_alpha101(matrices)
    # results: dict[str, pd.DataFrame | None]  (alpha_001 … alpha_101)
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import re

from .alpha_formulas_utils import (
    delay, delta, rank, ts_sum, ts_mean, ts_std, ts_max, ts_min, ts_rank,
    corr, cov, sign, log, absv, emax, emin, scale, decay_linear, ts_argmax,
    ts_argmin, product, adv, returns,
)
from .alpha_compute import compute_engine_alpha_methods, default_alpha_n_jobs

# ─── Aliases matching the alpha101 reference naming ───────────────────────────
sma = ts_mean          # simple moving average (rolling mean)
stddev = ts_std
correlation = corr
covariance = cov
ts_sum_fn = ts_sum


def signed_power(x, a):
    return sign(x) * (absv(x) ** a)


class Alpha101Engine:
    """Computes all 101 alpha factors from a dictionary of market-data matrices.

    Each matrix is a date-indexed, symbol-columned DataFrame as returned by
    ``build_matrices`` in ``alpha_ops.py``.

    Alphas that require industry-neutralization (IndNeutralize) or market-cap
    data return None and are omitted from the output.

    Args:
        matrices: dict with keys ``open``, ``high``, ``low``, ``close``,
            ``volume``, optionally ``vwap``.
    """

    def __init__(self, matrices: dict) -> None:
        self.open = matrices["open"]
        self.high = matrices["high"]
        self.low = matrices["low"]
        self.close = matrices["close"]
        self.volume = matrices["volume"]
        self.vwap = self._derive_vwap(matrices)
        self.returns = returns(self.close)

    def _derive_vwap(self, matrices: dict) -> pd.DataFrame:
        if "vwap" in matrices:
            return matrices["vwap"]

        adjfactor = matrices.get("adjfactor", 1.0)
        volume = self.volume.replace(0, np.nan)
        if "amount" in matrices:
            amount = matrices["amount"]
        elif "adjfactor" in matrices:
            amount = self.close / adjfactor.replace(0, np.nan) * self.volume
        else:
            amount = self.close * self.volume
        return amount / volume * adjfactor

    # ─── Alpha formulas ───────────────────────────────────────────────────────

    def alpha001(self):
        # rank(Ts_ArgMax(SignedPower(((returns < 0) ? stddev(returns, 20) : close), 2.), 5)) - 0.5
        inner = self.close.copy()
        inner[self.returns < 0] = stddev(self.returns, 20)
        return rank(ts_argmax(inner ** 2, 5)) - 0.5

    def alpha002(self):
        # -1 * correlation(rank(delta(log(volume), 2)), rank((close - open) / open), 6)
        df = -1 * correlation(rank(delta(log(self.volume), 2)), rank((self.close - self.open) / self.open), 6)
        return df.replace([-np.inf, np.inf], 0)

    def alpha003(self):
        # -1 * correlation(rank(open), rank(volume), 10)
        return (-1 * correlation(rank(self.open), rank(self.volume), 10)).replace([-np.inf, np.inf], 0)

    def alpha004(self):
        # -1 * Ts_Rank(rank(low), 9)
        return -1 * ts_rank(rank(self.low), 9)

    def alpha005(self):
        # rank(open - sum(vwap, 10) / 10) * (-1 * abs(rank(close - vwap)))
        return rank(self.open - ts_sum(self.vwap, 10) / 10) * (-1 * absv(rank(self.close - self.vwap)))

    def alpha006(self):
        # -1 * correlation(open, volume, 10)
        return (-1 * correlation(self.open, self.volume, 10)).replace([-np.inf, np.inf], 0)

    def alpha007(self):
        # (adv20 < volume) ? ((-1 * ts_rank(abs(delta(close, 7)), 60)) * sign(delta(close, 7))) : (-1)
        adv20 = adv(self.volume, 20)
        alpha = -1 * ts_rank(absv(delta(self.close, 7)), 60) * sign(delta(self.close, 7))
        alpha[adv20 >= self.volume] = -1
        return alpha

    def alpha008(self):
        # -1 * rank((sum(open, 5) * sum(returns, 5)) - delay((sum(open, 5) * sum(returns, 5)), 10))
        return -1 * rank(
            ts_sum(self.open, 5) * ts_sum(self.returns, 5)
            - delay(ts_sum(self.open, 5) * ts_sum(self.returns, 5), 10)
        )

    def alpha009(self):
        # ts_min(delta(close, 1), 5) > 0 → delta(close, 1)
        # ts_max(delta(close, 1), 5) < 0 → delta(close, 1)
        # else → -1 * delta(close, 1)
        d = delta(self.close, 1)
        alpha = -1 * d
        alpha[(ts_min(d, 5) > 0) | (ts_max(d, 5) < 0)] = d
        return alpha

    def alpha010(self):
        d = delta(self.close, 1)
        alpha = -1 * d
        alpha[(ts_min(d, 4) > 0) | (ts_max(d, 4) < 0)] = d
        return rank(alpha)

    def alpha011(self):
        return (rank(ts_max(self.vwap - self.close, 3)) + rank(ts_min(self.vwap - self.close, 3))) * rank(delta(self.volume, 3))

    def alpha012(self):
        return sign(delta(self.volume, 1)) * (-1 * delta(self.close, 1))

    def alpha013(self):
        return -1 * rank(covariance(rank(self.close), rank(self.volume), 5))

    def alpha014(self):
        df = correlation(self.open, self.volume, 10).replace([-np.inf, np.inf], 0)
        return -1 * rank(delta(self.returns, 3)) * df

    def alpha015(self):
        df = correlation(rank(self.high), rank(self.volume), 3).replace([-np.inf, np.inf], 0)
        return -1 * ts_sum(rank(df), 3)

    def alpha016(self):
        return -1 * rank(covariance(rank(self.high), rank(self.volume), 5))

    def alpha017(self):
        adv20 = adv(self.volume, 20)
        return -1 * (
            rank(ts_rank(self.close, 10))
            * rank(delta(delta(self.close, 1), 1))
            * rank(ts_rank(self.volume / adv20, 5))
        )

    def alpha018(self):
        df = correlation(self.close, self.open, 10).replace([-np.inf, np.inf], 0)
        return -1 * rank(stddev(absv(self.close - self.open), 5) + (self.close - self.open) + df)

    def alpha019(self):
        return (
            -1 * sign((self.close - delay(self.close, 7)) + delta(self.close, 7))
            * (1 + rank(1 + ts_sum(self.returns, 250)))
        )

    def alpha020(self):
        return -1 * (
            rank(self.open - delay(self.high, 1))
            * rank(self.open - delay(self.close, 1))
            * rank(self.open - delay(self.low, 1))
        )

    def alpha021(self):
        # Conditional on rolling mean ± stddev vs close-period mean
        cond1 = sma(self.close, 8) + stddev(self.close, 8) < sma(self.close, 2)
        cond2 = sma(self.close, 2) < sma(self.close, 8) - stddev(self.close, 8)
        cond3 = adv(self.volume, 20) / self.volume < 1
        return (cond1 | (~cond1 & ~cond2 & ~cond3)).astype(int) * (-2) + 1

    def alpha022(self):
        df = correlation(self.high, self.volume, 5).replace([-np.inf, np.inf], 0)
        return -1 * delta(df, 5) * rank(stddev(self.close, 20))

    def alpha023(self):
        cond = sma(self.high, 20) < self.high
        alpha = pd.DataFrame(0.0, index=self.close.index, columns=self.close.columns)
        alpha[cond] = -1 * delta(self.high, 2).fillna(0)
        return alpha

    def alpha024(self):
        cond = delta(sma(self.close, 100), 100) / delay(self.close, 100) <= 0.05
        alpha = -1 * delta(self.close, 3)
        alpha[cond] = -1 * (self.close - ts_min(self.close, 100))
        return alpha

    def alpha025(self):
        adv20 = adv(self.volume, 20)
        return rank((-1 * self.returns) * adv20 * self.vwap * (self.high - self.close))

    def alpha026(self):
        df = correlation(ts_rank(self.volume, 5), ts_rank(self.high, 5), 5).replace([-np.inf, np.inf], 0)
        return -1 * ts_max(df, 3)

    def alpha027(self):
        alpha = rank(sma(correlation(rank(self.volume), rank(self.vwap), 6), 2) / 2.0)
        return sign((alpha - 0.5) * (-2))

    def alpha028(self):
        adv20 = adv(self.volume, 20)
        df = correlation(adv20, self.low, 5).replace([-np.inf, np.inf], 0)
        return scale(df + (self.high + self.low) / 2 - self.close)

    def alpha029(self):
        return (
            ts_min(rank(rank(scale(log(ts_sum(rank(rank(-1 * rank(delta(self.close - 1, 5)))), 2))))), 5)
            + ts_rank(delay(-1 * self.returns, 6), 5)
        )

    def alpha030(self):
        d = delta(self.close, 1)
        inner = sign(d) + sign(delay(d, 1)) + sign(delay(d, 2))
        return (1.0 - rank(inner)) * ts_sum(self.volume, 5) / ts_sum(self.volume, 20)

    def alpha031(self):
        adv20 = adv(self.volume, 20)
        df = correlation(adv20, self.low, 12).replace([-np.inf, np.inf], 0)
        return (
            rank(rank(rank(decay_linear(-1 * rank(rank(delta(self.close, 10))), 10))))
            + rank(-1 * delta(self.close, 3))
            + sign(scale(df))
        )

    def alpha032(self):
        corr_230 = self.vwap.rolling(230, min_periods=180).corr(delay(self.close, 5))
        corr_230 = corr_230.replace([np.inf, -np.inf], np.nan)
        return (
            scale((ts_sum(self.close, 7) / 7) - self.close)
            + 20 * scale(corr_230)
        )

    def alpha033(self):
        return rank(-1 + self.open / self.close)

    def alpha034(self):
        inner = (stddev(self.returns, 2) / stddev(self.returns, 5)).replace([-np.inf, np.inf], 1).fillna(1)
        return rank(2 - rank(inner) - rank(delta(self.close, 1)))

    def alpha035(self):
        return (
            ts_rank(self.volume, 32)
            * (1 - ts_rank(self.close + self.high - self.low, 16))
            * (1 - ts_rank(self.returns, 32))
        )

    def alpha036(self):
        adv20 = adv(self.volume, 20)
        return (
            2.21 * rank(correlation(self.close - self.open, delay(self.volume, 1), 15))
            + 0.7 * rank(self.open - self.close)
            + 0.73 * rank(ts_rank(delay(-1 * self.returns, 6), 5))
            + rank(absv(correlation(self.vwap, adv20, 6)))
            + 0.6 * rank((sma(self.close, 200) / 200 - self.open) * (self.close - self.open))
        )

    def alpha037(self):
        return rank(correlation(delay(self.open - self.close, 1), self.close, 200)) + rank(self.open - self.close)

    def alpha038(self):
        inner = (self.close / self.open).replace([-np.inf, np.inf], 1).fillna(1)
        return -1 * rank(ts_rank(self.open, 10)) * rank(inner)

    def alpha039(self):
        adv20 = adv(self.volume, 20)
        return (
            -1 * rank(delta(self.close, 7) * (1 - rank(decay_linear(self.volume / adv20, 9))))
            * (1 + rank(sma(self.returns, 250)))
        )

    def alpha040(self):
        return -1 * rank(stddev(self.high, 10)) * correlation(self.high, self.volume, 10)

    def alpha041(self):
        return (self.high * self.low) ** 0.5 - self.vwap

    def alpha042(self):
        return rank(self.vwap - self.close) / rank(self.vwap + self.close)

    def alpha043(self):
        adv20 = adv(self.volume, 20)
        return ts_rank(self.volume / adv20, 20) * ts_rank(-1 * delta(self.close, 7), 8)

    def alpha044(self):
        return (-1 * correlation(self.high, rank(self.volume), 5)).replace([-np.inf, np.inf], 0)

    def alpha045(self):
        df = correlation(self.close, self.volume, 2).replace([-np.inf, np.inf], 0)
        return -1 * rank(sma(delay(self.close, 5), 20)) * df * rank(correlation(ts_sum(self.close, 5), ts_sum(self.close, 20), 2))

    def alpha046(self):
        inner = (delay(self.close, 20) - delay(self.close, 10)) / 10 - (delay(self.close, 10) - self.close) / 10
        alpha = -1 * delta(self.close, 1)
        alpha[inner < 0] = 1
        alpha[inner > 0.25] = -1
        return alpha

    def alpha047(self):
        adv20 = adv(self.volume, 20)
        return (
            (rank(1 / self.close) * self.volume / adv20)
            * (self.high * rank(self.high - self.close) / (ts_sum(self.high, 5) / 5))
            - rank(self.vwap - delay(self.vwap, 5))
        )

    def alpha048(self):
        return None  # Requires industry neutralization (IndClass.subindustry)

    def alpha049(self):
        inner = (delay(self.close, 20) - delay(self.close, 10)) / 10 - (delay(self.close, 10) - self.close) / 10
        alpha = -1 * delta(self.close, 1)
        alpha[inner < -0.1] = 1
        return alpha

    def alpha050(self):
        return -1 * ts_max(rank(correlation(rank(self.volume), rank(self.vwap), 5)), 5)

    def alpha051(self):
        inner = (delay(self.close, 20) - delay(self.close, 10)) / 10 - (delay(self.close, 10) - self.close) / 10
        alpha = -1 * delta(self.close, 1)
        alpha[inner < -0.05] = 1
        return alpha

    def alpha052(self):
        return (
            (-1 * delta(ts_min(self.low, 5), 5))
            * rank((ts_sum(self.returns, 240) - ts_sum(self.returns, 20)) / 220)
            * ts_rank(self.volume, 5)
        )

    def alpha053(self):
        inner = (self.close - self.low).replace(0, 0.0001)
        return -1 * delta((self.close - self.low - (self.high - self.close)) / inner, 9)

    def alpha054(self):
        inner = (self.low - self.high).replace(0, -0.0001)
        return -1 * (self.low - self.close) * self.open ** 5 / (inner * self.close ** 5)

    def alpha055(self):
        divisor = (ts_max(self.high, 12) - ts_min(self.low, 12)).replace(0, 0.0001)
        inner = (self.close - ts_min(self.low, 12)) / divisor
        return (-1 * correlation(rank(inner), rank(self.volume), 6)).replace([-np.inf, np.inf], 0)

    def alpha056(self):
        return None  # Requires market cap data

    def alpha057(self):
        return 0 - (self.close - self.vwap) / decay_linear(rank(ts_argmax(self.close, 30)), 2)

    def alpha058(self):
        return None  # Requires IndClass.sector

    def alpha059(self):
        return None  # Requires IndClass.industry

    def alpha060(self):
        divisor = (self.high - self.low).replace(0, 0.0001)
        inner = ((self.close - self.low) - (self.high - self.close)) * self.volume / divisor
        return -(2 * scale(rank(inner)) - scale(rank(ts_argmax(self.close, 10))))

    def alpha061(self):
        adv180 = adv(self.volume, 180)
        return (rank(self.vwap - ts_min(self.vwap, 16)) < rank(correlation(self.vwap, adv180, 18))).astype(int)

    def alpha062(self):
        adv20 = adv(self.volume, 20)
        return (
            (rank(correlation(self.vwap, sma(adv20, 22), 10))
             < rank((rank(self.open) + rank(self.open)) < (rank((self.high + self.low) / 2) + rank(self.high))))
        ) * -1

    def alpha063(self):
        return None  # Requires IndClass.industry

    def alpha064(self):
        adv120 = adv(self.volume, 120)
        cond = (
            rank(correlation(sma(self.open * 0.178404 + self.low * (1 - 0.178404), 12), sma(adv120, 12), 16))
            < rank(delta((self.high + self.low) / 2 * 0.178404 + self.vwap * (1 - 0.178404), 3))
        )
        alpha = pd.DataFrame(1.0, index=self.close.index, columns=self.close.columns)
        alpha[cond] = -1.0
        return alpha

    def alpha065(self):
        adv60 = adv(self.volume, 60)
        return (
            rank(correlation(self.open * 0.00817205 + self.vwap * (1 - 0.00817205), sma(adv60, 9), 6))
            < rank(self.open - ts_min(self.open, 14))
        ) * -1

    def alpha066(self):
        return (
            rank(decay_linear(delta(self.vwap, 4), 7))
            + ts_rank(decay_linear(
                ((self.low * 0.96633 + self.low * (1 - 0.96633)) - self.vwap)
                / (self.open - (self.high + self.low) / 2).replace(0, np.nan), 11), 7)
        ) * -1

    def alpha067(self):
        return None  # Requires IndClass.sector + IndClass.subindustry

    def alpha068(self):
        adv15 = adv(self.volume, 15)
        cond = ts_rank(correlation(rank(self.high), rank(adv15), 8), 13) < rank(
            delta(self.close * 0.518371 + self.low * (1 - 0.518371), 1)
        )
        alpha = pd.DataFrame(1.0, index=self.close.index, columns=self.close.columns)
        alpha[cond] = -1.0
        return alpha

    def alpha069(self):
        return None  # Requires IndClass.industry

    def alpha070(self):
        return None  # Requires IndClass.industry

    def alpha071(self):
        adv180 = adv(self.volume, 180)
        p1 = ts_rank(decay_linear(correlation(ts_rank(self.close, 3), ts_rank(adv180, 12), 18), 4), 16)
        p2 = ts_rank(decay_linear(rank((self.low + self.open) - (self.vwap + self.vwap)) ** 2, 16), 4)
        return emax(p1, p2)

    def alpha072(self):
        adv40 = adv(self.volume, 40)
        return (
            rank(decay_linear(correlation((self.high + self.low) / 2, adv40, 9), 10))
            / rank(decay_linear(correlation(ts_rank(self.vwap, 4), ts_rank(self.volume, 19), 7), 3))
        )

    def alpha073(self):
        p1 = rank(decay_linear(delta(self.vwap, 5), 3))
        p2 = ts_rank(decay_linear(
            (delta(self.open * 0.147155 + self.low * (1 - 0.147155), 2)
             / (self.open * 0.147155 + self.low * (1 - 0.147155)).replace(0, np.nan)) * -1, 3), 17)
        return -1 * emax(p1, p2)

    def alpha074(self):
        adv30 = adv(self.volume, 30)
        return (
            rank(correlation(self.close, sma(adv30, 37), 15))
            < rank(correlation(rank(self.high * 0.0261661 + self.vwap * (1 - 0.0261661)), rank(self.volume), 11))
        ) * -1

    def alpha075(self):
        adv50 = adv(self.volume, 50)
        return (rank(correlation(self.vwap, self.volume, 4)) < rank(correlation(rank(self.low), rank(adv50), 12))).astype(int)

    def alpha076(self):
        return None  # Requires IndClass.sector

    def alpha077(self):
        adv40 = adv(self.volume, 40)
        p1 = rank(decay_linear((self.high + self.low) / 2 + self.high - self.vwap - self.high, 20))
        p2 = rank(decay_linear(correlation((self.high + self.low) / 2, adv40, 3), 6))
        return emin(p1, p2)

    def alpha078(self):
        adv40 = adv(self.volume, 40)
        return rank(
            correlation(ts_sum(self.low * 0.352233 + self.vwap * (1 - 0.352233), 20), ts_sum(adv40, 20), 7)
        ) ** rank(correlation(rank(self.vwap), rank(self.volume), 6))

    def alpha079(self):
        return None  # Requires IndClass.sector

    def alpha080(self):
        return None  # Requires IndClass.industry

    def alpha081(self):
        adv10 = adv(self.volume, 10)
        return (
            rank(log(product(rank(rank(correlation(self.vwap, ts_sum(adv10, 50), 8)) ** 4), 15)))
            < rank(correlation(rank(self.vwap), rank(self.volume), 5))
        ) * -1

    def alpha082(self):
        return None  # Requires IndClass.sector

    def alpha083(self):
        return (
            rank(delay((self.high - self.low) / (ts_sum(self.close, 5) / 5), 2))
            * rank(rank(self.volume))
            / ((self.high - self.low) / (ts_sum(self.close, 5) / 5) / (self.vwap - self.close).replace(0, np.nan))
        )

    def alpha084(self):
        return signed_power(ts_rank(self.vwap - ts_max(self.vwap, 15), 20), delta(self.close, 4))

    def alpha085(self):
        adv30 = adv(self.volume, 30)
        return rank(
            correlation(self.high * 0.876703 + self.close * (1 - 0.876703), adv30, 10)
        ) ** rank(correlation(ts_rank((self.high + self.low) / 2, 4), ts_rank(self.volume, 10), 7))

    def alpha086(self):
        adv20 = adv(self.volume, 20)
        cond = ts_rank(correlation(self.close, ts_sum(adv20, 15), 6), 20) < rank(
            (self.open + self.close) - (self.vwap + self.open)
        )
        alpha = pd.DataFrame(1.0, index=self.close.index, columns=self.close.columns)
        alpha[cond] = -1.0
        return alpha

    def alpha087(self):
        return None  # Requires IndClass.industry

    def alpha088(self):
        adv60 = adv(self.volume, 60)
        p1 = rank(decay_linear((rank(self.open) + rank(self.low)) - (rank(self.high) + rank(self.close)), 8))
        p2 = ts_rank(decay_linear(correlation(ts_rank(self.close, 8), ts_rank(adv60, 21), 8), 7), 3)
        return emin(p1, p2)

    def alpha089(self):
        return None  # Requires IndClass.industry

    def alpha090(self):
        return None  # Requires IndClass.subindustry

    def alpha091(self):
        return None  # Requires IndClass.industry

    def alpha092(self):
        adv30 = adv(self.volume, 30)
        p1 = ts_rank(decay_linear(((self.high + self.low) / 2 + self.close) < (self.low + self.open), 15), 19)
        p2 = ts_rank(decay_linear(correlation(rank(self.low), rank(adv30), 8), 7), 7)
        return emin(p1, p2)

    def alpha093(self):
        return None  # Requires IndClass.industry

    def alpha094(self):
        adv60 = adv(self.volume, 60)
        return (
            rank(self.vwap - ts_min(self.vwap, 12))
            ** ts_rank(correlation(ts_rank(self.vwap, 20), ts_rank(adv60, 4), 18), 3)
        ) * -1

    def alpha095(self):
        adv40 = adv(self.volume, 40)
        cond = rank(self.open - ts_min(self.open, 12)) < ts_rank(
            rank(correlation(ts_sum((self.high + self.low) / 2, 19), ts_sum(adv40, 19), 13)) ** 5,
            12,
        )
        alpha = pd.DataFrame(-1.0, index=self.close.index, columns=self.close.columns)
        alpha[cond] = 1.0
        return alpha

    def alpha096(self):
        adv60 = adv(self.volume, 60)
        p1 = ts_rank(decay_linear(correlation(rank(self.vwap), rank(self.volume), 3), 4), 8)
        p2 = ts_rank(decay_linear(ts_argmax(correlation(ts_rank(self.close, 7), ts_rank(adv60, 4), 3), 12), 13), 13)
        return -1 * emax(p1, p2)

    def alpha097(self):
        return None  # Requires IndClass.industry

    def alpha098(self):
        adv5 = adv(self.volume, 5)
        adv15 = adv(self.volume, 15)
        return (
            rank(decay_linear(correlation(self.vwap, sma(adv5, 26), 5), 7))
            - rank(decay_linear(ts_rank(ts_argmin(correlation(rank(self.open), rank(adv15), 21), 9), 7), 8))
        )

    def alpha099(self):
        adv60 = adv(self.volume, 60)
        return (
            rank(correlation(ts_sum((self.high + self.low) / 2, 20), ts_sum(adv60, 20), 9))
            < rank(correlation(self.low, self.volume, 6))
        ) * -1

    def alpha100(self):
        return None  # Requires IndClass.subindustry + indneutralize

    def alpha101(self):
        return (self.close - self.open) / ((self.high - self.low) + 0.001)


def normalize_alpha101_names(alpha_names=None) -> list[str]:
    if alpha_names is None:
        return [f"alpha_{i:03d}" for i in range(1, 102)]
    if isinstance(alpha_names, str):
        if alpha_names.strip().lower() in {"all", "*"}:
            return [f"alpha_{i:03d}" for i in range(1, 102)]
        alpha_names = [alpha_names]

    normalized: list[str] = []
    for raw_name in alpha_names:
        text = str(raw_name).strip().lower()
        if not text:
            continue
        match = re.fullmatch(r"(?:alpha_?)?(\d{1,3})", text)
        if not match:
            raise ValueError(f"Invalid Alpha101 name: {raw_name!r}. Use names like 'alpha_095' or '95'.")
        alpha_number = int(match.group(1))
        if alpha_number < 1 or alpha_number > 101:
            raise ValueError(f"Unsupported Alpha101 column: alpha_{alpha_number:03d}. Valid range is alpha_001 to alpha_101.")
        alpha_name = f"alpha_{alpha_number:03d}"
        if alpha_name not in normalized:
            normalized.append(alpha_name)

    if not normalized:
        raise ValueError("alpha_columns must contain at least one Alpha101 name.")
    return normalized


def compute_all_alpha101(
    matrices: dict,
    alpha_names=None,
    *,
    n_jobs: int | None = None,
    show_progress: bool = True,
) -> dict[str, pd.DataFrame]:
    """Compute all implementable Alpha101 factors.

    Args:
        matrices: dict of field_name → date×symbol DataFrames (from ``build_matrices``).
        alpha_names: optional iterable of requested names, such as ``alpha_095`` or ``95``.
        n_jobs: worker threads; defaults to the hardware logical CPU count.

    Returns:
        dict mapping ``alpha_001`` … ``alpha_101`` to DataFrames (or omitted if None).
    """
    engine = Alpha101Engine(matrices)
    names = normalize_alpha101_names(alpha_names)

    return compute_engine_alpha_methods(
        engine=engine,
        names=names,
        n_jobs=default_alpha_n_jobs() if n_jobs in (None, "") else n_jobs,
        show_progress=show_progress,
        label="Alpha101",
    )
