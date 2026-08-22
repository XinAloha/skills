"""Alpha191 formula engine.

Implements the 191 alpha factors based on JoinQuant Alpha191 formulas.
Reference implementation source: JoinQuant official factor documentation and
JoinQuant factor-value API corrections used by the upstream local skill.

Usage::

    from alpha_runtime.alpha191_formulas import compute_all_alpha191

    results = compute_all_alpha191(matrices)
    # results: dict[str, pd.DataFrame | None]  (alpha_001 … alpha_191)
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import re
from typing import Optional

from .alpha_formulas_utils import (
    delay, delta, rank, ts_sum, ts_mean, ts_std, ts_max, ts_min, ts_rank,
    corr, cov, ema, sign, log, absv, emax, emin, scale, decay_linear,
    regbeta, lowday, highday, count, sumif, product, ts_argmax, ts_argmin,
    wma, row_max, row_min, adv, sequence, returns,
)
from .alpha_compute import compute_engine_alpha_methods, default_alpha_n_jobs

# ─── Alias to match Alpha191 reference naming ─────────────────────────────────
Delay = delay
Delta = delta
Rank = rank
Sum = ts_sum
Mean = ts_mean
Std = ts_std
Tsmax = ts_max
Tsmin = ts_min
Tsrank = ts_rank
Corr = corr
Cov = cov
Sma = ema          # NOTE: Sma in Alpha191 is EWM, not simple moving average
Sign = sign
Log = log
Abs = absv
Max = emax
Min = emin
Scale = scale
Decaylinear = decay_linear
Regbeta = regbeta
Lowday = lowday
Highday = highday
Count = count
Sumif = sumif
Prod = product
Tsargmax = ts_argmax
Tsargmin = ts_argmin
Wma = wma
Rowmax = row_max
Rowmin = row_min
Sequence = sequence


class Alpha191Engine:
    """Computes all 191 alpha factors from a dictionary of market-data matrices.

    Each matrix is a date-indexed, symbol-columned DataFrame as returned by
    ``build_matrices`` in ``alpha_ops.py``.

    Args:
        matrices: dict with keys ``open``, ``high``, ``low``, ``close``,
            ``volume``, optionally ``vwap``, ``amount``.
        benchmark_matrices: optional dict with ``close``/``open`` for index data
            (required only by alphas 075, 181, 182).
    """

    def __init__(
        self,
        matrices: dict,
        benchmark_matrices: Optional[dict] = None,
    ) -> None:
        self.open = matrices["open"]
        self.high = matrices["high"]
        self.low = matrices["low"]
        self.close = matrices["close"]
        self.volume = matrices["volume"]
        self.amount = self._derive_amount(matrices)
        self.vwap = self._derive_vwap(matrices)
        self.returns = returns(self.close)

        bm = benchmark_matrices or {}
        self.benchmark_close: Optional[pd.DataFrame] = bm.get("close")
        self.benchmark_open: Optional[pd.DataFrame] = bm.get("open")

    # ─── Helpers ──────────────────────────────────────────────────────────────

    def _derive_amount(self, matrices: dict) -> pd.DataFrame:
        if "amount" in matrices:
            return matrices["amount"]
        return self.close * self.volume

    def _derive_vwap(self, matrices: dict) -> pd.DataFrame:
        if "vwap" in matrices:
            return matrices["vwap"]
        return self.amount / self.volume.replace(0, np.nan)

    def _safe_div(self, num, denom) -> pd.DataFrame:
        return num / denom.replace(0, np.nan)

    # ─── Alpha formulas ───────────────────────────────────────────────────────

    def alpha001(self):
        return -1 * Corr(Rank(Delta(Log(self.volume), 1)), Rank((self.close - self.open) / self.open), 6)

    def alpha002(self):
        denom = self._safe_div(self.high - self.low, self.high - self.low)  # just get the non-zero mask
        val = (self.close - self.low) - (self.high - self.close)
        return -1 * Delta(val / (self.high - self.low).replace(0, np.nan), 1)

    def alpha003(self):
        prev = Delay(self.close, 1)
        cond_eq = self.close == prev
        cond_up = self.close > prev
        part = (self.close - Min(self.low, prev)).where(cond_up, other=(self.close - Max(self.high, prev)))
        return Sum(part.where(~cond_eq, other=0.0), 6)

    def alpha004(self):
        vol_ratio = self.volume / Mean(self.volume, 20)
        cond1 = (Sum(self.close, 8) / 8 + Std(self.close, 8)) < (Sum(self.close, 2) / 2)
        cond2 = (Sum(self.close, 2) / 2) < (Sum(self.close, 8) / 8 - Std(self.close, 8))
        cond3_inner = vol_ratio >= 1
        arr = np.where(cond1, -1, np.where(cond2, 1, np.where(cond3_inner, 1, -1)))
        return pd.DataFrame(arr.astype(float), index=self.close.index, columns=self.close.columns)

    def alpha005(self):
        return -1 * Tsmax(Corr(Tsrank(self.volume, 5), Tsrank(self.high, 5), 5), 3)

    def alpha006(self):
        return -1 * Rank(Sign(Delta(self.open * 0.85 + self.high * 0.15, 4)))

    def alpha007(self):
        return (Rank(Tsmax(self.vwap - self.close, 3)) + Rank(Tsmin(self.vwap - self.close, 3))) * Rank(Delta(self.volume, 3))

    def alpha008(self):
        return Rank(Delta((self.high + self.low) / 2 * 0.2 + self.vwap * 0.8, 4) * -1)

    def alpha009(self):
        vol = self.volume.replace(0, np.nan)
        mid_delta = (self.high + self.low) / 2 - (Delay(self.high, 1) + Delay(self.low, 1)) / 2
        return Sma(mid_delta * (self.high - self.low) / vol, 7, 2)

    def alpha010(self):
        cond = self.returns < 0
        inner = Std(self.returns, 20).where(cond, other=self.close)
        return Rank(Tsmax(inner ** 2, 5))

    def alpha011(self):
        denom = (self.high - self.low).replace(0, np.nan)
        return Sum(((self.close - self.low) - (self.high - self.close)) / denom * self.volume, 6)

    def alpha012(self):
        return Rank(self.open - Sum(self.vwap, 10) / 10) * (1 * Rank(Abs(self.close - self.vwap)))

    def alpha013(self):
        return (self.high * self.low) ** 0.5 - self.vwap

    def alpha014(self):
        return self.close - Delay(self.close, 5)

    def alpha015(self):
        return self.open / Delay(self.close, 1) - 1

    def alpha016(self):
        return -1 * Tsmax(Rank(Corr(Rank(self.volume), Rank(self.vwap), 5)), 5)

    def alpha017(self):
        result = Rank(self.vwap - Tsmax(self.vwap, 15)) ** Delta(self.close, 5)
        return result.clip(upper=1e12)

    def alpha018(self):
        return self.close / Delay(self.close, 5)

    def alpha019(self):
        prev5 = Delay(self.close, 5)
        cond_lt = self.close < prev5
        cond_eq = self.close == prev5
        cond_gt = self.close > prev5
        part_lt = (self.close - prev5) / prev5.replace(0, np.nan)
        part_gt = (self.close - prev5) / self.close.replace(0, np.nan)
        result = part_lt.where(cond_lt, other=0.0)
        result = result.where(~cond_eq, other=0.0)
        result = result.where(cond_lt | cond_eq, other=part_gt)
        return result

    def alpha020(self):
        return (self.close - Delay(self.close, 6)) / Delay(self.close, 6) * 100

    def alpha021(self):
        return Regbeta(Mean(self.close, 6), Sequence(6))

    def alpha022(self):
        mean6 = Mean(self.close, 6)
        dev = (self.close - mean6) / mean6.replace(0, np.nan)
        return Sma(dev - Delay(dev, 3), 12, 1)

    def alpha023(self):
        cond = self.close > Delay(self.close, 1)
        up = Std(self.close, 20).where(cond, other=0.0)
        dn = Std(self.close, 20).where(~cond, other=0.0)
        s_up = Sma(up, 20, 1)
        s_dn = Sma(dn, 20, 1)
        return 100 * s_up / (s_up + s_dn).replace(0, np.nan)

    def alpha024(self):
        return Sma(self.close - Delay(self.close, 5), 5, 1)

    def alpha025(self):
        return (
            -1 * Rank(Delta(self.close, 7) * (1 - Rank(Decaylinear(self.volume / Mean(self.volume, 20), 9))))
        ) * (1 + Rank(Sum(self.returns, 250)))

    def alpha026(self):
        return (Sum(self.close, 7) / 7 - self.close) + Corr(self.vwap, Delay(self.close, 5), 230)

    def alpha027(self):
        A = ((self.close - Delay(self.close, 3)) / Delay(self.close, 3) * 100
             + (self.close - Delay(self.close, 6)) / Delay(self.close, 6) * 100)
        return Wma(A, 12)

    def alpha028(self):
        rng = (Tsmax(self.high, 9) - Tsmin(self.low, 9)).replace(0, np.nan)
        kd = (self.close - Tsmin(self.low, 9)) / rng * 100
        return 3 * Sma(kd, 3, 1) - 2 * Sma(Sma(kd, 3, 1), 3, 1)

    def alpha029(self):
        return (self.close - Delay(self.close, 6)) / Delay(self.close, 6) * self.volume

    def alpha030(self):
        return None  # Requires Fama-French market factors; not available

    def alpha031(self):
        return (self.close - Mean(self.close, 12)) / Mean(self.close, 12) * 100

    def alpha032(self):
        return -1 * Sum(Rank(Corr(Rank(self.high), Rank(self.volume), 3)), 3)

    def alpha033(self):
        return (
            ((-1 * Tsmin(self.low, 5)) + Delay(Tsmin(self.low, 5), 5))
            * Rank((Sum(self.returns, 240) - Sum(self.returns, 20)) / 220)
            * Tsrank(self.volume, 5)
        )

    def alpha034(self):
        return Mean(self.close, 12) / self.close

    def alpha035(self):
        return Min(
            Rank(Decaylinear(Delta(self.open, 1), 15)),
            Rank(Decaylinear(Corr(self.volume, self.open * 0.65 + self.open * 0.35, 17), 7)),
        ) * 1

    def alpha036(self):
        return Rank(Sum(Corr(Rank(self.volume), Rank(self.vwap), 6), 2))

    def alpha037(self):
        inner = Sum(self.open, 5) * Sum(self.returns, 5)
        return -1 * Rank(inner - Delay(inner, 10))

    def alpha038(self):
        cond = Sum(self.high, 20) / 20 < self.high
        return (-1 * Delta(self.high, 2)).where(cond, other=0.0)

    def alpha039(self):
        return (
            Rank(Decaylinear(Delta(self.close, 2), 8))
            - Rank(Decaylinear(Corr(self.vwap * 0.3 + self.open * 0.7, Sum(Mean(self.volume, 180), 37), 14), 12))
        ) * 1

    def alpha040(self):
        cond = self.close > Delay(self.close, 1)
        part_up = self.volume.where(cond, other=0.0)
        part_dn = self.volume.where(~cond, other=0.0)
        return Sum(part_up, 26) / Sum(part_dn, 26).replace(0, np.nan) * 100

    def alpha041(self):
        return Rank(Tsmax(Delta(self.vwap, 3), 5)) * -1

    def alpha042(self):
        return (-1 * Rank(Std(self.high, 10))) * Corr(self.high, self.volume, 10)

    def alpha043(self):
        cond_up = self.close > Delay(self.close, 1)
        cond_dn = self.close < Delay(self.close, 1)
        part = self.volume.where(cond_up, other=(-self.volume).where(cond_dn, other=0.0))
        return Sum(part, 6)

    def alpha044(self):
        return (
            Tsrank(Decaylinear(Corr(self.low, Mean(self.volume, 10), 7), 6), 4)
            + Tsrank(Decaylinear(Delta(self.vwap, 3), 10), 15)
        )

    def alpha045(self):
        return Rank(Delta(self.close * 0.6 + self.open * 0.4, 1)) * Rank(Corr(self.vwap, Mean(self.volume, 150), 15))

    def alpha046(self):
        return (Mean(self.close, 3) + Mean(self.close, 6) + Mean(self.close, 12) + Mean(self.close, 24)) / (4 * self.close)

    def alpha047(self):
        rng = (Tsmax(self.high, 6) - Tsmin(self.low, 6)).replace(0, np.nan)
        return Sma((Tsmax(self.high, 6) - self.close) / rng * 100, 9, 1)

    def alpha048(self):
        s = (Sign(self.close - Delay(self.close, 1))
             + Sign(Delay(self.close, 1) - Delay(self.close, 2))
             + Sign(Delay(self.close, 2) - Delay(self.close, 3)))
        return -1 * Rank(s) * Sum(self.volume, 5) / Sum(self.volume, 20).replace(0, np.nan)

    def _tr_parts(self):
        """Helper: compute parts for alphas 049-051 (TR-based)."""
        mx = Max(Abs(self.high - Delay(self.high, 1)), Abs(self.low - Delay(self.low, 1)))
        return mx

    def alpha049(self):
        prev_sum = Delay(self.high, 1) + Delay(self.low, 1)
        curr_sum = self.high + self.low
        mx = self._tr_parts()
        down = mx.where(curr_sum < prev_sum, other=0.0)
        up = mx.where(curr_sum > prev_sum, other=0.0)
        sum_down = Sum(down, 12)
        sum_up = Sum(up, 12)
        denom = (sum_down + sum_up).replace(0, np.nan)
        return sum_down / denom

    def alpha050(self):
        prev_sum = Delay(self.high, 1) + Delay(self.low, 1)
        curr_sum = self.high + self.low
        mx = self._tr_parts()
        up = mx.where(curr_sum > prev_sum, other=0.0)
        down = mx.where(curr_sum < prev_sum, other=0.0)
        sum_up = Sum(up, 12)
        sum_down = Sum(down, 12)
        denom = (sum_up + sum_down).replace(0, np.nan)
        return (sum_up - sum_down) / denom

    def alpha051(self):
        prev_sum = Delay(self.high, 1) + Delay(self.low, 1)
        curr_sum = self.high + self.low
        mx = self._tr_parts()
        up = mx.where(curr_sum > prev_sum, other=0.0)
        down = mx.where(curr_sum < prev_sum, other=0.0)
        sum_up = Sum(up, 12)
        sum_down = Sum(down, 12)
        denom = (sum_up + sum_down).replace(0, np.nan)
        return sum_up / denom

    def alpha052(self):
        tp = (self.high + self.low + self.close) / 3
        return (
            Sum(Max(self.high - Delay(tp, 1), 0), 26)
            / Sum(Max(Delay(tp, 1) - self.low, 0), 26).replace(0, np.nan)
            * 100
        )

    def alpha053(self):
        cond = self.close > Delay(self.close, 1)
        return Count(cond, 12) / 12 * 100

    def alpha054(self):
        return 1 * Rank((Std(Abs(self.close - self.open), 5) + (self.close - self.open)) + Corr(self.close, self.open, 10))

    def alpha055(self):
        A = Abs(self.high - Delay(self.close, 1))
        B = Abs(self.low - Delay(self.close, 1))
        C = Abs(self.high - Delay(self.low, 1))
        D = Abs(Delay(self.close, 1) - Delay(self.open, 1))
        cond1 = (A > B) & (A > C)
        cond2 = (B > C) & (B > A)
        cond3 = ~cond1 & ~cond2
        denom_vals = pd.DataFrame(
            np.where(cond1, A + B / 2 + D / 4, np.where(cond2, B + A / 2 + D / 4, C + D / 4)),
            index=self.close.index, columns=self.close.columns,
        ).replace(0, np.nan)
        part0 = 16 * (self.close + (self.close - self.open) / 2 - Delay(self.open, 1))
        return Sum(part0 / denom_vals * Max(A, B), 20)

    def alpha056(self):
        A = Rank(self.open - Tsmin(self.open, 12))
        B = Rank(Rank(Corr(Sum((self.high + self.low) / 2, 19), Sum(Mean(self.volume, 40), 19), 13)) ** 5)
        cond = A < B
        return pd.DataFrame(
            np.where(cond, 1.0, -1.0),
            index=self.close.index, columns=self.close.columns,
        )

    def alpha057(self):
        rng = (Tsmax(self.high, 9) - Tsmin(self.low, 9)).replace(0, np.nan)
        return Sma((self.close - Tsmin(self.low, 9)) / rng * 100, 3, 1)

    def alpha058(self):
        cond = self.close > Delay(self.close, 1)
        return Count(cond, 20) / 20 * 100

    def alpha059(self):
        cond_eq = self.close == Delay(self.close, 1)
        cond_up = self.close > Delay(self.close, 1)
        cond_dn = self.close < Delay(self.close, 1)
        part_up = self.close - Min(self.low, Delay(self.close, 1))
        part_dn = self.close - Max(self.high, Delay(self.close, 1))
        part = part_up.where(cond_up, other=part_dn.where(cond_dn, other=0.0))
        return Sum(part, 20)

    def alpha060(self):
        denom = (self.high - self.low).replace(0, np.nan)
        return Sum(((self.close - self.low) - (self.high - self.close)) / denom * self.volume, 20)

    def alpha061(self):
        return (
            Max(Rank(Decaylinear(Delta(self.vwap, 1), 12)),
                Rank(Decaylinear(Rank(Corr(self.low, Mean(self.volume, 80), 8)), 17))) * -1
        )

    def alpha062(self):
        return -1 * Corr(self.high, Rank(self.volume), 5)

    def alpha063(self):
        d = Abs(self.close - Delay(self.close, 1))
        return Sma(Max(self.close - Delay(self.close, 1), 0), 6, 1) / Sma(d, 6, 1).replace(0, np.nan) * 100

    def alpha064(self):
        return (
            Max(Rank(Decaylinear(Corr(Rank(self.vwap), Rank(self.volume), 4), 4)),
                Rank(Decaylinear(Tsmax(Corr(Rank(self.close), Rank(Mean(self.volume, 60)), 4), 13), 14))) * -1
        )

    def alpha065(self):
        return Mean(self.close, 6) / self.close

    def alpha066(self):
        return (self.close - Mean(self.close, 6)) / Mean(self.close, 6) * 100

    def alpha067(self):
        d = Abs(self.close - Delay(self.close, 1))
        return Sma(Max(self.close - Delay(self.close, 1), 0), 24, 1) / Sma(d, 24, 1).replace(0, np.nan) * 100

    def alpha068(self):
        vol = self.volume.replace(0, np.nan)
        mid_delta = (self.high + self.low) / 2 - (Delay(self.high, 1) + Delay(self.low, 1)) / 2
        return Sma(mid_delta * (self.high - self.low) / vol, 15, 2) * 100

    def alpha069(self):
        cond_dtm = self.open <= Delay(self.open, 1)
        cond_dbm = self.open >= Delay(self.open, 1)
        DTM = Max(self.high - self.open, self.open - Delay(self.open, 1)).where(~cond_dtm, other=0.0)
        DBM = Max(self.open - self.low, self.open - Delay(self.open, 1)).where(~cond_dbm, other=0.0)
        sdtm, sdbm = Sum(DTM, 20), Sum(DBM, 20)
        cond3 = sdtm > sdbm
        cond4 = sdtm == sdbm
        part = (
            ((sdtm - sdbm) / sdtm.replace(0, np.nan)).where(cond3,
             other=(0.0 * sdtm).where(cond4,
             other=(sdtm - sdbm) / sdbm.replace(0, np.nan)))
        )
        return part

    def alpha070(self):
        return Std(self.amount, 6)

    def alpha071(self):
        return (self.close - Mean(self.close, 24)) / Mean(self.close, 24) * 100

    def alpha072(self):
        rng = (Tsmax(self.high, 6) - Tsmin(self.low, 6)).replace(0, np.nan)
        return Sma((Tsmax(self.high, 6) - self.close) / rng * 100, 15, 1)

    def alpha073(self):
        return (
            Tsrank(Decaylinear(Decaylinear(Corr(self.close, self.volume, 10), 16), 4), 5)
            - Rank(Decaylinear(Corr(self.vwap, Mean(self.volume, 30), 4), 3))
        ) * -1

    def alpha074(self):
        return (
            Rank(Corr(Sum(self.low * 0.35 + self.vwap * 0.65, 20), Sum(Mean(self.volume, 40), 20), 7))
            + Rank(Corr(Rank(self.vwap), Rank(self.volume), 6))
        )

    def alpha075(self):
        if self.benchmark_close is None or self.benchmark_open is None:
            return None
        cond = (self.close > self.open) & (self.benchmark_close < self.benchmark_open)
        bm_cond = self.benchmark_close < self.benchmark_open
        return Count(cond, 50) / Count(bm_cond, 50).replace(0, np.nan)

    def alpha076(self):
        return Std(Abs((self.close / Delay(self.close, 1) - 1)) / self.volume.replace(0, np.nan), 20) / Mean(
            Abs((self.close / Delay(self.close, 1) - 1)) / self.volume.replace(0, np.nan), 20
        ).replace(0, np.nan)

    def alpha077(self):
        return Min(
            Rank(Decaylinear(((self.high + self.low) / 2 + self.high) - (self.vwap + self.high), 20)),
            Rank(Decaylinear(Corr((self.high + self.low) / 2, Mean(self.volume, 40), 3), 6)),
        )

    def alpha078(self):
        tp = (self.high + self.low + self.close) / 3
        mean_tp = Mean(tp, 12)
        denom = Mean(Abs(self.close - mean_tp), 12) * 0.015
        return (tp - mean_tp) / denom.replace(0, np.nan)

    def alpha079(self):
        d = Abs(self.close - Delay(self.close, 1))
        return Sma(Max(self.close - Delay(self.close, 1), 0), 12, 1) / Sma(d, 12, 1).replace(0, np.nan) * 100

    def alpha080(self):
        return (self.volume - Delay(self.volume, 5)) / Delay(self.volume, 5) * 100

    def alpha081(self):
        return Sma(self.volume, 21, 2)

    def alpha082(self):
        rng = (Tsmax(self.high, 6) - Tsmin(self.low, 6)).replace(0, np.nan)
        return Sma((Tsmax(self.high, 6) - self.close) / rng * 100, 20, 1)

    def alpha083(self):
        return -1 * Rank(Cov(Rank(self.high), Rank(self.volume), 5))

    def alpha084(self):
        cond_up = self.close > Delay(self.close, 1)
        cond_dn = self.close < Delay(self.close, 1)
        part = self.volume.where(cond_up, other=(-self.volume).where(cond_dn, other=0.0))
        return Sum(part, 20)

    def alpha085(self):
        return Tsrank(self.volume / Mean(self.volume, 20), 20) * Tsrank(-1 * Delta(self.close, 7), 8)

    def alpha086(self):
        A = ((Delay(self.close, 20) - Delay(self.close, 10)) / 10 - (Delay(self.close, 10) - self.close) / 10)
        cond1 = A > 0.25
        cond2 = A < 0.0
        cond3 = (A >= 0.0) & (A <= 0.25)
        arr = np.where(cond1, -1, np.where(cond2, 1, -1 * (self.close - Delay(self.close, 1))))
        return pd.DataFrame(arr, index=self.close.index, columns=self.close.columns)

    def alpha087(self):
        return (
            Rank(Decaylinear(Delta(self.vwap, 4), 7))
            + Tsrank(Decaylinear(
                (self.high - self.vwap)
                / (self.open - (self.high + self.low) / 2).replace(0, np.nan),
                11), 7)
        ) * -1

    def alpha088(self):
        return (self.close - Delay(self.close, 20)) / Delay(self.close, 20)

    def alpha089(self):
        return 2 * (Sma(self.close, 13, 2) - Sma(self.close, 27, 2)
                    - Sma(Sma(self.close, 13, 2) - Sma(self.close, 27, 2), 10, 2))

    def alpha090(self):
        return Rank(Corr(Rank(self.vwap), Rank(self.volume), 5)) * -1

    def alpha091(self):
        return (
            Rank(self.close - Tsmax(self.close, 5)) * Rank(Corr(Mean(self.volume, 40), self.low, 5))
        ) * -1

    def alpha092(self):
        return (
            Max(Rank(Decaylinear(Delta(self.close * 0.35 + self.vwap * 0.65, 2), 3)),
                Tsrank(Decaylinear(Abs(Corr(Mean(self.volume, 180), self.close, 13)), 5), 15)) * -1
        )

    def alpha093(self):
        cond = self.open >= Delay(self.open, 1)
        part = Max(self.open - self.low, self.open - Delay(self.open, 1)).where(~cond, other=0.0)
        return Sum(part, 20)

    def alpha094(self):
        cond_up = self.close > Delay(self.close, 1)
        cond_dn = self.close < Delay(self.close, 1)
        part = self.volume.where(cond_up, other=(-self.volume).where(cond_dn, other=0.0))
        return Sum(part, 30)

    def alpha095(self):
        return Std(self.amount, 20)

    def alpha096(self):
        rng = (Tsmax(self.high, 9) - Tsmin(self.low, 9)).replace(0, np.nan)
        return Sma(Sma((self.close - Tsmin(self.low, 9)) / rng * 100, 3, 1), 3, 1)

    def alpha097(self):
        return Std(self.volume, 10)

    def alpha098(self):
        cond = Delta(Sum(self.close, 100) / 100, 100) / Delay(self.close, 100) <= 0.05
        return (-1 * (self.close - Tsmin(self.close, 100))).where(cond, other=-1 * Delta(self.close, 3))

    def alpha099(self):
        return -1 * Rank(Cov(Rank(self.close), Rank(self.volume), 5))

    def alpha100(self):
        return Std(self.volume, 20)

    def alpha101(self):
        rank1 = Rank(Corr(self.close, Sum(Mean(self.volume, 30), 37), 15))
        rank2 = Rank(Corr(Rank(self.high * 0.1 + self.vwap * 0.9), Rank(self.volume), 11))
        cond = rank1 < rank2
        return pd.DataFrame(
            np.where(cond, -1.0, 1.0),
            index=self.close.index, columns=self.close.columns,
        )

    def alpha102(self):
        d = Abs(self.volume - Delay(self.volume, 1))
        return Sma(Max(self.volume - Delay(self.volume, 1), 0), 6, 1) / Sma(d, 6, 1).replace(0, np.nan) * 100

    def alpha103(self):
        return (20 - Lowday(self.low, 20)) / 20 * 100

    def alpha104(self):
        return -1 * (Delta(Corr(self.high, self.volume, 5), 5) * Rank(Std(self.close, 20)))

    def alpha105(self):
        return 1 * Corr(Rank(self.open), Rank(self.volume), 10)

    def alpha106(self):
        return self.close - Delay(self.close, 20)

    def alpha107(self):
        return (
            (-1 * Rank(self.open - Delay(self.high, 1)))
            * Rank(self.open - Delay(self.close, 1))
            * Rank(self.open - Delay(self.low, 1))
        )

    def alpha108(self):
        return (Rank(self.high - Tsmin(self.high, 2)) ** Rank(Corr(self.vwap, Mean(self.volume, 120), 6))) * -1

    def alpha109(self):
        hl = self.high - self.low
        return Sma(hl, 10, 2) / Sma(Sma(hl, 10, 2), 10, 2).replace(0, np.nan)

    def alpha110(self):
        return (
            Sum(Max(self.high - Delay(self.close, 1), 0), 20)
            / Sum(Max(Delay(self.close, 1) - self.low, 0), 20).replace(0, np.nan)
            * 100
        )

    def alpha111(self):
        denom = (self.high - self.low).replace(0, np.nan)
        v = self.volume * ((self.close - self.low) - (self.high - self.close)) / denom
        return Sma(v, 11, 2) - Sma(v, 4, 2)

    def alpha112(self):
        cond_up = (self.close - Delay(self.close, 1)) > 0
        cond_dn = (self.close - Delay(self.close, 1)) < 0
        d = self.close - Delay(self.close, 1)
        part1 = d.where(cond_up, other=0.0)
        part2 = Abs(d).where(cond_dn, other=0.0)
        s1, s2 = Sum(part1, 12), Sum(part2, 12)
        return (s1 - s2) / (s1 + s2).replace(0, np.nan) * 100

    def alpha113(self):
        return -1 * (
            Rank(Sum(Delay(self.close, 5), 20) / 20)
            * Corr(self.close, self.volume, 2)
            * Rank(Corr(Sum(self.close, 5), Sum(self.close, 20), 2))
        )

    def alpha114(self):
        mean5 = Sum(self.close, 5) / 5
        hl5 = (self.high - self.low) / mean5.replace(0, np.nan)
        return (
            Rank(Delay(hl5, 2)) * Rank(Rank(self.volume))
            / (hl5 / (self.vwap - self.close).replace(0, np.nan))
        )

    def alpha115(self):
        return (
            Rank(Corr(self.high * 0.9 + self.close * 0.1, Mean(self.volume, 30), 10))
            ** Rank(Corr(Tsrank((self.high + self.low) / 2, 4), Tsrank(self.volume, 10), 7))
        )

    def alpha116(self):
        return Regbeta(self.close, Sequence(20))

    def alpha117(self):
        return (
            Tsrank(self.volume, 32)
            * (1 - Tsrank(self.close + self.high - self.low, 16))
            * (1 - Tsrank(self.returns, 32))
        )

    def alpha118(self):
        return Sum(self.high - self.open, 20) / Sum(self.open - self.low, 20).replace(0, np.nan) * 100

    def alpha119(self):
        return (
            Rank(Decaylinear(Corr(self.vwap, Sum(Mean(self.volume, 5), 26), 5), 7))
            - Rank(Decaylinear(Tsrank(Tsmin(Corr(Rank(self.open), Rank(Mean(self.volume, 15)), 21), 9), 7), 8))
        )

    def alpha120(self):
        return Rank(self.vwap - self.close) / Rank(self.vwap + self.close).replace(0, np.nan)

    def alpha121(self):
        return (
            Rank(self.vwap - Tsmin(self.vwap, 12))
            ** Tsrank(Corr(Tsrank(self.vwap, 20), Tsrank(Mean(self.volume, 60), 2), 18), 3)
        ) * -1

    def alpha122(self):
        triple = Sma(Sma(Sma(Log(self.close), 13, 2), 13, 2), 13, 2)
        return (triple - Delay(triple, 1)) / Delay(triple, 1).replace(0, np.nan)

    def alpha123(self):
        A = Rank(Corr(Sum((self.high + self.low) / 2, 20), Sum(Mean(self.volume, 60), 20), 9))
        B = Rank(Corr(self.low, self.volume, 6))
        cond = A < B
        return (-cond.astype(float)).where(cond, other=1.0)

    def alpha124(self):
        return (self.close - self.vwap) / Decaylinear(Rank(Tsmax(self.close, 30)), 2).replace(0, np.nan)

    def alpha125(self):
        return (
            Rank(Decaylinear(Corr(self.vwap, Mean(self.volume, 80), 17), 20))
            / Rank(Decaylinear(Delta(self.close * 0.5 + self.vwap * 0.5, 3), 16)).replace(0, np.nan)
        )

    def alpha126(self):
        return (self.close + self.high + self.low) / 3

    def alpha127(self):
        x = 100 * (self.close - Tsmax(self.close, 12)) / Tsmax(self.close, 12).replace(0, np.nan)
        return Abs(x)

    def alpha128(self):
        tp = (self.high + self.low + self.close) / 3
        cond = tp > Delay(tp, 1)
        part1 = (tp * self.volume).where(cond, other=0.0)
        part2 = (tp * self.volume).where(~cond, other=0.0)
        return 100 - 100 / (1 + Sum(part1, 14) / Sum(part2, 14).replace(0, np.nan))

    def alpha129(self):
        d = self.close - Delay(self.close, 1)
        cond = d < 0
        return Sum(Abs(d).where(cond, other=0.0), 12)

    def alpha130(self):
        return (
            Rank(Decaylinear(Corr((self.high + self.low) / 2, Mean(self.volume, 40), 9), 10))
            / Rank(Decaylinear(Corr(Rank(self.vwap), Rank(self.volume), 7), 3)).replace(0, np.nan)
        )

    def alpha131(self):
        return Rank(Delta(self.vwap, 1)) ** Tsrank(Corr(self.close, Mean(self.volume, 50), 18), 18)

    def alpha132(self):
        return Mean(self.amount, 20)

    def alpha133(self):
        return (20 - Highday(self.high, 20)) / 20 * 100 - (20 - Lowday(self.low, 20)) / 20 * 100

    def alpha134(self):
        return (self.close - Delay(self.close, 12)) / Delay(self.close, 12) * self.volume

    def alpha135(self):
        return Sma(Delay(self.close / Delay(self.close, 20), 1), 20, 1)

    def alpha136(self):
        return -1 * Rank(Delta(self.returns, 3)) * Corr(self.open, self.volume, 10)

    def alpha137(self):
        A = Abs(self.high - Delay(self.close, 1))
        B = Abs(self.low - Delay(self.close, 1))
        C = Abs(self.high - Delay(self.low, 1))
        D = Abs(Delay(self.close, 1) - Delay(self.open, 1))
        cond1 = (A > B) & (A > C)
        cond2 = (B > C) & (B > A)
        denom_vals = pd.DataFrame(
            np.where(cond1, A + B / 2 + D / 4, np.where(cond2, B + A / 2 + D / 4, C + D / 4)),
            index=self.close.index, columns=self.close.columns,
        ).replace(0, np.nan)
        part0 = 16 * (self.close + (self.close - self.open) / 2 - Delay(self.open, 1))
        return part0 / denom_vals * Max(A, B)

    def alpha138(self):
        return (
            Rank(Decaylinear(Delta(self.low * 0.7 + self.vwap * 0.3, 3), 20))
            - Tsrank(Decaylinear(Tsrank(Corr(Tsrank(self.low, 8), Tsrank(Mean(self.volume, 60), 17), 5), 19), 16), 7)
        ) * -1

    def alpha139(self):
        return -1 * Corr(self.open, self.volume, 10)

    def alpha140(self):
        return Min(
            Rank(Decaylinear((Rank(self.open) + Rank(self.low)) - (Rank(self.high) + Rank(self.close)), 8)),
            Tsrank(Decaylinear(Corr(Tsrank(self.close, 8), Tsrank(Mean(self.volume, 60), 20), 8), 7), 3),
        )

    def alpha141(self):
        return Rank(Corr(Rank(self.high), Rank(Mean(self.volume, 15)), 9)) * -1

    def alpha142(self):
        return (
            (-1 * Rank(Tsrank(self.close, 10)))
            * Rank(Delta(Delta(self.close, 1), 1))
            * Rank(Tsrank(self.volume / Mean(self.volume, 20), 5))
        )

    def alpha143(self):
        prev_close = Delay(self.close, 1)
        ret = (self.close - prev_close) / prev_close.replace(0, np.nan)
        cond = self.close > prev_close

        out = pd.DataFrame(np.nan, index=self.close.index, columns=self.close.columns, dtype=float)
        prev_self = pd.Series(1.0, index=self.close.columns, dtype=float)
        for dt in self.close.index:
            current = prev_self.copy()
            valid = cond.loc[dt].fillna(False) & ret.loc[dt].notna()
            current.loc[valid] = ret.loc[dt, valid] * prev_self.loc[valid]
            out.loc[dt] = current
            prev_self = current
        return out

    def alpha144(self):
        cond = self.close < Delay(self.close, 1)
        part = Abs(self.close / Delay(self.close, 1) - 1) / self.amount.replace(0, np.nan)
        return Sumif(part, 20, cond) / Count(cond, 20).replace(0, np.nan)

    def alpha145(self):
        return (Mean(self.volume, 9) - Mean(self.volume, 26)) / Mean(self.volume, 12).replace(0, np.nan) * 100

    def alpha146(self):
        ret = (self.close - Delay(self.close, 1)) / Delay(self.close, 1)
        sma_ret = Sma(ret, 61, 2)
        dev = ret - sma_ret
        denom = Sma(dev ** 2, 61, 2).replace(0, np.nan)
        return Mean(dev, 20) * dev / denom

    def alpha147(self):
        return Regbeta(Mean(self.close, 12), Sequence(12))

    def alpha148(self):
        cond = (
            Rank(Corr(self.open, Sum(Mean(self.volume, 60), 9), 6))
            < Rank(self.open - Tsmin(self.open, 14))
        )
        return pd.DataFrame(
            np.where(cond, -1.0, 1.0),
            index=self.close.index, columns=self.close.columns,
        )

    def alpha149(self):
        return None  # Requires benchmark index data with filtering; not available

    def alpha150(self):
        return (self.close + self.high + self.low) / 3 * self.volume

    def alpha151(self):
        return Sma(self.close - Delay(self.close, 20), 20, 1)

    def alpha152(self):
        inner = Sma(Delay(self.close / Delay(self.close, 9), 1), 9, 1)
        return Sma(Mean(Delay(inner, 1), 12) - Mean(Delay(inner, 1), 26), 9, 1)

    def alpha153(self):
        return (Mean(self.close, 3) + Mean(self.close, 6) + Mean(self.close, 12) + Mean(self.close, 24)) / 4

    def alpha154(self):
        cond = (self.vwap - Tsmin(self.vwap, 16)) < Corr(self.vwap, Mean(self.volume, 180), 18)
        return pd.DataFrame(
            np.where(cond, 1.0, -1.0),
            index=self.close.index, columns=self.close.columns,
        )

    def alpha155(self):
        return (Sma(self.volume, 13, 2) - Sma(self.volume, 27, 2)
                - Sma(Sma(self.volume, 13, 2) - Sma(self.volume, 27, 2), 10, 2))

    def alpha156(self):
        base = self.open * 0.15 + self.low * 0.85
        return (
            Max(Rank(Decaylinear(Delta(self.vwap, 5), 3)),
                Rank(Decaylinear(
                    Delta(base, 2) / base.replace(0, np.nan) - 1, 3))) * -1
        )

    def alpha157(self):
        inner = -1 * Rank(Delta(self.close - 1, 5))
        return (
            Tsmin(product(Rank(Rank(Log(Sum(Tsmin(Rank(Rank(inner)), 2), 1)))), 1), 5)
            + Tsrank(Delay(-1 * self.returns, 6), 5)
        )

    def alpha158(self):
        return ((self.high - Sma(self.close, 15, 2)) - (self.low - Sma(self.close, 15, 2))) / self.close

    def alpha159(self):
        prev_close = Delay(self.close, 1)
        denom6 = Sum(Max(self.high, prev_close) - Min(self.low, prev_close), 6).replace(0, np.nan)
        denom12 = Sum(Max(self.high, prev_close) - Min(self.low, prev_close), 12).replace(0, np.nan)
        denom24 = Sum(Max(self.high, prev_close) - Min(self.low, prev_close), 24).replace(0, np.nan)
        return (
            (self.close - Sum(Min(self.low, prev_close), 6)) / denom6 * 12 * 24
            + (self.close - Sum(Min(self.low, prev_close), 12)) / denom12 * 6 * 24
            + (self.close - Sum(Min(self.low, prev_close), 24)) / denom24 * 6 * 24
        ) * 100 / (6 * 12 + 6 * 24 + 12 * 24)

    def alpha160(self):
        cond = self.close <= Delay(self.close, 1)
        part = Std(self.close, 20).where(cond, other=0.0)
        return Sma(part, 20, 1)

    def alpha161(self):
        return Mean(
            Max(Max(self.high - self.low, Abs(Delay(self.close, 1) - self.high)),
                Abs(Delay(self.close, 1) - self.low)), 12
        )

    def alpha162(self):
        d = Abs(self.close - Delay(self.close, 1))
        rsi = Sma(Max(self.close - Delay(self.close, 1), 0), 12, 1) / Sma(d, 12, 1).replace(0, np.nan) * 100
        mn = Tsmin(rsi, 12)
        mx = Tsmax(rsi, 12)
        return (rsi - mn) / (mx - mn).replace(0, np.nan)

    def alpha163(self):
        return Rank((-1 * self.returns) * Mean(self.volume, 20) * self.vwap * (self.high - self.close))

    def alpha164(self):
        prev_close = Delay(self.close, 1)
        cond = self.close > prev_close
        diff = self.close - prev_close
        safe_diff = diff.where(diff.abs() >= 0.01, np.sign(diff).replace(0, np.nan) * 0.01)
        inner = (1 / safe_diff).where(cond, other=1.0)
        denom = (self.high - self.low).replace(0, np.nan)
        return Sma((inner - Tsmin(inner, 12)) / denom * 100, 13, 2)

    def alpha165(self):
        x = Sum(self.close - Mean(self.close, 48), 48)
        p1 = Rowmax(x)
        p2 = Rowmin(x)
        p3 = Std(self.close, 48)
        return -1 * (x.sub(p1, axis=0)).div(p3.replace(0, np.nan), axis=0).add(p2, axis=0)

    def alpha166(self):
        ret = self.close / Delay(self.close, 1) - 1
        p1 = -20 * (20 - 1) ** 1.5 * Sum(ret - Mean(ret, 20), 20)
        p2 = (20 - 1) * (20 - 2) * (Sum(Mean(self.close / Delay(self.close, 1), 20) ** 2, 20)) ** 1.5
        return p1 / p2.replace(0, np.nan)

    def alpha167(self):
        cond = self.close > Delay(self.close, 1)
        d = (self.close - Delay(self.close, 1)).where(cond, other=0.0)
        return Sum(d, 12)

    def alpha168(self):
        return -1 * self.volume / Mean(self.volume, 20)

    def alpha169(self):
        inner = Sma(self.close - Delay(self.close, 1), 9, 1)
        return Sma(Mean(Delay(inner, 1), 12) - Mean(Delay(inner, 1), 26), 10, 1)

    def alpha170(self):
        return (
            (Rank(1 / self.close) * self.volume / Mean(self.volume, 20))
            * (self.high * Rank(self.high - self.close) / (Sum(self.high, 5) / 5).replace(0, np.nan))
            - Rank(self.vwap - Delay(self.vwap, 5))
        )

    def alpha171(self):
        denom = ((self.close - self.high) * self.close ** 5).replace(0, np.nan)
        return -1 * (self.low - self.close) * self.open ** 5 / denom

    def alpha172(self):
        TR = Max(Max(self.high - self.low, Abs(self.high - Delay(self.close, 1))), Abs(self.low - Delay(self.close, 1)))
        HD = self.high - Delay(self.high, 1)
        LD = Delay(self.low, 1) - self.low
        cond1 = (LD > 0) & (LD > HD)
        cond2 = (HD > 0) & (HD > LD)
        part1 = LD.where(cond1, other=0.0)
        part2 = HD.where(cond2, other=0.0)
        s_tr = Sum(TR, 14).replace(0, np.nan)
        dm_plus = Sum(part2, 14) * 100 / s_tr
        dm_minus = Sum(part1, 14) * 100 / s_tr
        denom = (dm_plus + dm_minus).replace(0, np.nan)
        return Mean(Abs(dm_minus - dm_plus) / denom * 100, 6)

    def alpha173(self):
        return (3 * Sma(self.close, 13, 2)
                - 2 * Sma(Sma(self.close, 13, 2), 13, 2)
                + Sma(Sma(Sma(Log(self.close), 13, 2), 13, 2), 13, 2))

    def alpha174(self):
        cond = self.close >= Delay(self.close, 1)
        part = Std(self.close, 20).where(cond, other=0.0)
        return Sma(part, 20, 1)

    def alpha175(self):
        return Mean(
            Max(Max(self.high - self.low, Abs(Delay(self.close, 1) - self.high)),
                Abs(Delay(self.close, 1) - self.low)), 6
        )

    def alpha176(self):
        rng = (Tsmax(self.high, 12) - Tsmin(self.low, 12)).replace(0, np.nan)
        return Corr(Rank((self.close - Tsmin(self.low, 12)) / rng), Rank(self.volume), 6)

    def alpha177(self):
        return (20 - Highday(self.high, 20)) / 20 * 100

    def alpha178(self):
        return (self.close - Delay(self.close, 1)) / Delay(self.close, 1) * self.volume

    def alpha179(self):
        return Rank(Corr(self.vwap, self.volume, 4)) * Rank(Corr(Rank(self.low), Rank(Mean(self.volume, 50)), 12))

    def alpha180(self):
        cond = Mean(self.volume, 20) < self.volume
        ts_r = (-1 * Tsrank(Abs(Delta(self.close, 7)), 60)) * Sign(Delta(self.close, 7))
        return ts_r.where(cond, other=-1 * self.volume)

    def alpha181(self):
        if self.benchmark_close is None:
            return None
        ret = self.close / Delay(self.close, 1) - 1
        bm_dev = self.benchmark_close - Mean(self.benchmark_close, 20)
        numer = Sum((ret - Mean(ret, 20)) - bm_dev ** 2, 20)
        denom = Sum(Abs(bm_dev) ** 3, 20).replace(0, np.nan)
        return numer / denom

    def alpha182(self):
        if self.benchmark_close is None or self.benchmark_open is None:
            return None
        cond = (
            ((self.close > self.open) & (self.benchmark_close > self.benchmark_open))
            | ((self.close < self.open) & (self.benchmark_close < self.benchmark_open))
        )
        return Count(cond, 20) / 20

    def alpha183(self):
        x = Sum(self.close - Mean(self.close, 24), 24)
        p1 = Rowmax(x)
        p2 = Rowmin(x)
        p3 = Std(self.close, 24)
        return -1 * (x.sub(p1, axis=0)).div(p3.replace(0, np.nan), axis=0).add(p2, axis=0)

    def alpha184(self):
        return (
            Rank(Corr(Delay(self.open - self.close, 1), self.close, 200))
            + Rank(self.open - self.close)
        )

    def alpha185(self):
        return Rank(-1 * (1 - self.open / self.close.replace(0, np.nan)) ** 2)

    def alpha186(self):
        TR = Max(Max(self.high - self.low, Abs(self.high - Delay(self.close, 1))), Abs(self.low - Delay(self.close, 1)))
        HD = self.high - Delay(self.high, 1)
        LD = Delay(self.low, 1) - self.low
        cond1 = (LD > 0) & (LD > HD)
        cond2 = (HD > 0) & (HD > LD)
        part1 = LD.where(cond1, other=0.0)
        part2 = HD.where(cond2, other=0.0)
        s_tr = Sum(TR, 14).replace(0, np.nan)
        dm_plus = Sum(part2, 14) * 100 / s_tr
        dm_minus = Sum(part1, 14) * 100 / s_tr
        denom = (dm_plus + dm_minus).replace(0, np.nan)
        adx = Mean(Abs(dm_minus - dm_plus) / denom * 100, 6)
        return (adx + Delay(adx, 6)) / 2

    def alpha187(self):
        cond = self.open <= Delay(self.open, 1)
        part = Max(self.high - self.open, self.open - Delay(self.open, 1)).where(~cond, other=0.0)
        return Sum(part, 20)

    def alpha188(self):
        hl = self.high - self.low
        return (hl - Sma(hl, 11, 2)) / Sma(hl, 11, 2).replace(0, np.nan) * 100

    def alpha189(self):
        return Mean(Abs(self.close - Mean(self.close, 6)), 6)

    def alpha190(self):
        ret = self.close / Delay(self.close, 1).replace(0, np.nan) - 1
        threshold = (self.close / Delay(self.close, 19).replace(0, np.nan)) ** (1 / 20) - 1
        diff2 = (ret - threshold) ** 2
        up = ret > threshold
        down = ret < threshold
        numerator = (Count(up, 20) - 1) * Sumif(diff2, 20, down)
        denominator = Count(down, 20) * Sumif(diff2, 20, up)
        ratio = numerator / denominator.replace(0, np.nan)
        ratio = ratio.where(ratio > 0).replace([np.inf, -np.inf], np.nan)
        return Log(ratio)

    def alpha191(self):
        return (Corr(Mean(self.volume, 20), self.low, 5) + (self.high + self.low) / 2) - self.close


def compute_all_alpha191(
    matrices: dict,
    benchmark_matrices: Optional[dict] = None,
    alpha_names=None,
    *,
    n_jobs: int | None = None,
    show_progress: bool = True,
) -> dict[str, pd.DataFrame]:
    """Compute all implementable Alpha191 factors.

    Args:
        matrices: dict of field_name → date×symbol DataFrames (from ``build_matrices``).
        benchmark_matrices: optional benchmark index matrices with ``close`` / ``open``.
        alpha_names: optional iterable of requested names, such as ``alpha_095`` or ``95``.
        n_jobs: worker threads; defaults to the hardware logical CPU count.

    Returns:
        dict mapping ``alpha_001`` … ``alpha_191`` to DataFrames (or None for skipped).
    """
    engine = Alpha191Engine(matrices, benchmark_matrices)
    names = normalize_alpha191_names(alpha_names)

    return compute_engine_alpha_methods(
        engine=engine,
        names=names,
        n_jobs=default_alpha_n_jobs() if n_jobs in (None, "") else n_jobs,
        show_progress=show_progress,
        label="Alpha191",
    )


def normalize_alpha191_names(alpha_names=None) -> list[str]:
    if alpha_names is None:
        return [f"alpha_{i:03d}" for i in range(1, 192)]
    if isinstance(alpha_names, str):
        if alpha_names.strip().lower() in {"all", "*"}:
            return [f"alpha_{i:03d}" for i in range(1, 192)]
        alpha_names = [alpha_names]

    normalized: list[str] = []
    for raw_name in alpha_names:
        text = str(raw_name).strip().lower()
        if not text:
            continue
        match = re.fullmatch(r"(?:alpha_?)?(\d{1,3})", text)
        if not match:
            raise ValueError(f"Invalid Alpha191 name: {raw_name!r}. Use names like 'alpha_095' or '95'.")
        alpha_number = int(match.group(1))
        if alpha_number < 1 or alpha_number > 191:
            raise ValueError(f"Unsupported Alpha191 column: alpha_{alpha_number:03d}. Valid range is alpha_001 to alpha_191.")
        alpha_name = f"alpha_{alpha_number:03d}"
        if alpha_name not in normalized:
            normalized.append(alpha_name)

    if not normalized:
        raise ValueError("alpha_columns must contain at least one Alpha191 name.")
    return normalized
