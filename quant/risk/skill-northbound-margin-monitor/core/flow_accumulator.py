"""Daily flow direction history accumulator.

Accumulates ``stock_hsgt_fund_flow_summary_em`` snapshots (nb_flow) into a
persistent historical series at ``cache/nb_flow_history.parquet``.

This provides a directional signal time series (+1 inflow, -1 outflow) that
replaces the broken ``net_buy_amount`` column in ``stock_hsgt_hist_em``.
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class FlowAccumulator:
    """Accumulates daily nb_flow snapshots into a persistent historical series.

    Storage: ``cache/nb_flow_history.parquet`` (single cumulative file).
    Deduplication: by (date, market). Repeated runs are idempotent.

    Direction mapping:
        - 资金方向 containing "北" or "入" → +1 (inflow)
        - 资金方向 containing "南" or "出" → -1 (outflow)
        - otherwise → 0
    """

    def __init__(self, cache_root: str | Path = "cache") -> None:
        self._root = Path(cache_root)
        self._history_path = self._root / "nb_flow_history.parquet"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def accumulate(self, trade_date: str, nb_flow: pd.DataFrame) -> pd.DataFrame:
        """Parse today's nb_flow snapshot, merge into history, persist.

        Args:
            trade_date: YYYYMMDD trade date.
            nb_flow: Raw DataFrame from ``stock_hsgt_fund_flow_summary_em``.

        Returns:
            Full accumulated history DataFrame (all dates), sorted by date.
        """
        today_rows = self._parse_flow(trade_date, nb_flow)
        if not today_rows:
            return self.load_history()

        existing = self.load_history()
        if existing.empty:
            combined = pd.DataFrame(today_rows)
        else:
            new_df = pd.DataFrame(today_rows)
            combined = pd.concat([existing, new_df], ignore_index=True)
            # Dedup: keep latest entry for each (date, market)
            combined = combined.drop_duplicates(subset=["date", "market"], keep="last")
            combined = combined.sort_values(["date", "market"]).reset_index(drop=True)

        self._save_history(combined)
        return combined

    def load_history(self) -> pd.DataFrame:
        """Load accumulated history, or empty DataFrame if none exists."""
        if not self._history_path.exists():
            return pd.DataFrame()
        try:
            return pd.read_parquet(self._history_path)
        except Exception:
            logger.warning("Corrupt nb_flow_history, will rebuild from per-date cache")
            return pd.DataFrame()

    def rebuild_from_cache(self) -> pd.DataFrame:
        """Emergency rebuild: scan all ``cache/*/northbound_flow.parquet`` files.

        Use this if ``nb_flow_history.parquet`` is corrupted or deleted.
        """
        if not self._root.exists():
            return pd.DataFrame()

        all_rows: list[dict] = []
        for date_dir in sorted(self._root.iterdir()):
            if not date_dir.is_dir():
                continue
            flow_path = date_dir / "northbound_flow.parquet"
            if not flow_path.exists():
                continue
            try:
                nb_flow = pd.read_parquet(flow_path)
                trade_date = date_dir.name
                rows = self._parse_flow(trade_date, nb_flow)
                all_rows.extend(rows)
            except Exception:
                logger.warning("Skipping corrupt flow file: %s", flow_path)

        if not all_rows:
            logger.warning("Rebuild: no valid per-date flow files found")
            return pd.DataFrame()

        result = pd.DataFrame(all_rows)
        result = result.drop_duplicates(subset=["date", "market"], keep="last")
        result = result.sort_values(["date", "market"]).reset_index(drop=True)
        self._save_history(result)
        logger.info("Rebuilt flow history: %d rows, %d dates",
                     len(result), result["date"].nunique())
        return result

    def get_direction_series(self, aggregate: str = "daily") -> pd.DataFrame:
        """Return a clean direction time series for detector consumption.

        Args:
            aggregate: ``"daily"`` — one row per date with sum/avg across SH+SZ.
                       ``"market"`` — separate SH and SZ rows.

        Returns:
            DataFrame with columns:
            | For daily: date, direction_sum, direction_days,
            |           adv_sum, dec_sum, flat_sum, index_chg_avg
            | For market: date, market, direction, adv_count, dec_count,
            |             flat_count, index_chg_pct
        """
        history = self.load_history()
        if history.empty:
            return history

        if aggregate == "market":
            return history[["date", "market", "direction",
                           "adv_count", "dec_count", "flat_count",
                           "index_chg_pct"]].copy()

        # Daily aggregate
        daily = history.groupby("date").agg(
            direction_sum=("direction", "sum"),
            direction_days=("direction", lambda x: (x != 0).sum()),
            adv_sum=("adv_count", "sum"),
            dec_sum=("dec_count", "sum"),
            flat_sum=("flat_count", "sum"),
            index_chg_avg=("index_chg_pct", "mean"),
        ).reset_index()

        daily = daily.sort_values("date").reset_index(drop=True)
        return daily

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _parse_flow(self, trade_date: str, nb_flow: pd.DataFrame) -> list[dict]:
        """Parse nb_flow snapshot into a list of normalized row dicts.

        Each dict represents one market (SH or SZ) for the given date.
        Filters out 港股通 (southbound) rows.
        """
        if nb_flow is None or nb_flow.empty:
            return []

        # Column resolution: name match → positional fallback
        cols = list(nb_flow.columns)

        # Market/sector column
        sector_idx = self._find_col(cols, ["板块", "sector", "market", "segment"], 2)
        # Direction column
        dir_idx = self._find_col(cols, ["资金方向", "direction", "flow_direction"], 3)
        # Index change column
        idx_chg_idx = self._find_col(cols, ["指数涨跌幅", "index_change", "index_pct"], 12)
        # Advancing column
        adv_idx = self._find_col(cols, ["上涨数", "advancing", "adv_count", "up_count"], 8)
        # Declining column
        dec_idx = self._find_col(cols, ["下跌数", "declining", "dec_count", "down_count"], 10)
        # Flat column
        flat_idx = self._find_col(cols, ["持平数", "flat", "unchanged", "flat_count"], 9)

        rows: list[dict] = []
        for _, row in nb_flow.iterrows():
            sector = str(row.iloc[sector_idx]) if sector_idx < len(row) else ""
            if "港股通" in sector or "南向" in sector:
                continue  # only accumulate northbound (沪股通/深股通)

            market = self._normalize_market(sector)
            direction = self._parse_direction(
                str(row.iloc[dir_idx]) if dir_idx < len(row) else ""
            )

            adv = self._safe_int(row.iloc[adv_idx]) if adv_idx < len(row) else 0
            dec = self._safe_int(row.iloc[dec_idx]) if dec_idx < len(row) else 0
            flat = self._safe_int(row.iloc[flat_idx]) if flat_idx < len(row) else 0
            idx_chg = self._safe_float(row.iloc[idx_chg_idx]) if idx_chg_idx < len(row) else 0.0

            rows.append({
                "date": trade_date,
                "market": market,
                "direction": direction,
                "adv_count": adv,
                "dec_count": dec,
                "flat_count": flat,
                "index_chg_pct": idx_chg,
            })

        return rows

    def _save_history(self, df: pd.DataFrame) -> None:
        """Persist accumulated history to parquet."""
        self._root.mkdir(parents=True, exist_ok=True)
        df.to_parquet(self._history_path, index=False)
        logger.info("Flow history saved: %d rows, %d dates",
                     len(df), df["date"].nunique() if "date" in df.columns else 0)

    # ------------------------------------------------------------------
    # Static helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _find_col(columns: list[str], candidates: list[str], fallback_pos: int) -> int:
        """Find column index by name candidates, falling back to position."""
        for candidate in candidates:
            for i, col in enumerate(columns):
                if candidate in str(col):
                    return i
        return fallback_pos

    @staticmethod
    def _normalize_market(sector: str) -> str:
        """Normalize sector name to 'SH' or 'SZ'."""
        if "沪" in sector:
            return "SH"
        if "深" in sector:
            return "SZ"
        if "SH" in sector.upper():
            return "SH"
        if "SZ" in sector.upper():
            return "SZ"
        return sector[:2] if len(sector) >= 2 else sector

    @staticmethod
    def _parse_direction(dir_str: str) -> int:
        """Map direction string to +1 (inflow/north), -1 (outflow/south), or 0."""
        if not dir_str:
            return 0
        # Northbound inflow: 北向流入 / 资金流入
        if "北" in dir_str or "入" in dir_str:
            return 1
        # Northbound outflow: 南向流出 / 资金流出
        if "南" in dir_str or "出" in dir_str:
            return -1
        return 0

    @staticmethod
    def _safe_int(val) -> int:
        """Safely convert to int, returning 0 on failure."""
        try:
            return int(float(val))
        except (ValueError, TypeError):
            return 0

    @staticmethod
    def _safe_float(val) -> float:
        """Safely convert to float, returning 0.0 on failure."""
        try:
            v = float(val)
            return v if not np.isnan(v) else 0.0
        except (ValueError, TypeError):
            return 0.0
