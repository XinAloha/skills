"""Local Parquet cache for north-bound, margin, and stock info data.

Avoids re-fetching data on every run during the same day.
Cache is keyed by trade date (YYYYMMDD).

Cache directory::

    cache/
      20260630/
        northbound.parquet
        margin.parquet
        margin_detail.parquet
        stock_info.parquet
        .cache_meta.json
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

META_FILENAME = ".cache_meta.json"


class CacheManager:
    """Date-keyed Parquet cache for panorama monitor data."""

    def __init__(self, cache_root: str | Path = "cache") -> None:
        self._root = Path(cache_root)

    # -- public API --------------------------------------------------

    def has(self, trade_date: str) -> bool:
        """Check if cached data exists for *trade_date*."""
        if not self._root.exists():
            return False
        date_dir = self._root / trade_date
        return date_dir.is_dir() and (date_dir / "northbound.parquet").exists()

    def load(self, trade_date: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """Load cached (northbound, margin, margin_detail, stock_info, futures) for *trade_date*.

        Returns empty DataFrames on corrupt or missing cache files
        rather than crashing the pipeline.
        """
        date_dir = self._root / trade_date

        def _safe_read(name: str) -> pd.DataFrame:
            try:
                return pd.read_parquet(date_dir / name)
            except Exception:
                logger.warning("Corrupt or unreadable %s cache for %s, ignoring", name, trade_date)
                return pd.DataFrame()

        nb = _safe_read("northbound.parquet")
        mg = _safe_read("margin.parquet")
        md = _safe_read("margin_detail.parquet")
        info = _safe_read("stock_info.parquet")
        fut = _safe_read("futures.parquet")
        logger.info("Cache hit: %s (%d northbound rows)", trade_date, len(nb))
        return nb, mg, md, info, fut

    def load_meta(self, trade_date: str) -> dict:
        """Load cache metadata without reading parquet files."""
        date_dir = self._root / trade_date
        meta_path = date_dir / META_FILENAME
        if meta_path.exists():
            try:
                return json.loads(meta_path.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {}

    def save(
        self,
        trade_date: str,
        northbound_df: pd.DataFrame,
        margin_df: pd.DataFrame,
        margin_detail_df: pd.DataFrame,
        stock_info_df: pd.DataFrame,
        northbound_flow_df: pd.DataFrame | None = None,
        futures_df: pd.DataFrame | None = None,
        fetch_time: str = "",
    ) -> None:
        """Persist data to cache."""
        date_dir = self._root / trade_date
        date_dir.mkdir(parents=True, exist_ok=True)

        def _safe_parquet(df: pd.DataFrame, path: Path) -> None:
            """Write parquet, cleaning NaN strings in object columns first."""
            df = df.copy()
            for col in df.columns:
                if df[col].dtype == object:
                    # Replace string "NaN" / "nan" with None (parquet-compatible)
                    mask = df[col].astype(str).str.lower().isin(["nan", "<na>"])
                    df.loc[mask, col] = None
            df.to_parquet(path, index=False)

        _safe_parquet(northbound_df, date_dir / "northbound.parquet")
        _safe_parquet(margin_df, date_dir / "margin.parquet")
        _safe_parquet(margin_detail_df, date_dir / "margin_detail.parquet")
        _safe_parquet(stock_info_df, date_dir / "stock_info.parquet")
        if northbound_flow_df is not None and not northbound_flow_df.empty:
            _safe_parquet(northbound_flow_df, date_dir / "northbound_flow.parquet")
        if futures_df is not None and not futures_df.empty:
            _safe_parquet(futures_df, date_dir / "futures.parquet")

        nb_source = northbound_df.attrs.get("source", "unknown") if not northbound_df.empty else "none"
        mg_source = margin_df.attrs.get("source", "unknown") if not margin_df.empty else "none"
        meta = {
            "trade_date": trade_date,
            "northbound_rows": len(northbound_df),
            "margin_rows": len(margin_df),
            "margin_detail_rows": len(margin_detail_df),
            "stock_info_rows": len(stock_info_df),
            "northbound_source": nb_source,
            "margin_source": mg_source,
        }
        if fetch_time:
            meta["fetch_time"] = fetch_time
        (date_dir / META_FILENAME).write_text(
            json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        logger.info("Cache saved: %s", date_dir)

    def load_nb_flow(self, trade_date: str) -> pd.DataFrame:
        """Load cached northbound flow data for *trade_date*."""
        date_dir = self._root / trade_date
        flow_path = date_dir / "northbound_flow.parquet"
        if flow_path.exists():
            try:
                return pd.read_parquet(flow_path)
            except Exception:
                logger.warning("Corrupt northbound_flow cache for %s", trade_date)
        return pd.DataFrame()

    # -- Flow history (cumulative, not per-date) -------------------------

    def save_nb_flow_history(self, df: pd.DataFrame) -> None:
        """Save accumulated nb_flow history to cache root.

        Writes to ``cache/nb_flow_history.parquet`` (a single cumulative file).
        """
        self._root.mkdir(parents=True, exist_ok=True)
        df.to_parquet(self._root / "nb_flow_history.parquet", index=False)
        n_dates = df["date"].nunique() if "date" in df.columns else 0
        logger.info("Flow history saved: %d rows, %d dates", len(df), n_dates)

    def load_nb_flow_history(self) -> pd.DataFrame:
        """Load accumulated nb_flow history from cache root.

        Returns empty DataFrame if the file does not exist or is corrupt.
        """
        history_path = self._root / "nb_flow_history.parquet"
        if not history_path.exists():
            return pd.DataFrame()
        try:
            return pd.read_parquet(history_path)
        except Exception:
            logger.warning("Corrupt nb_flow_history, needs rebuild")
            return pd.DataFrame()

    # -- HKEX supplement cache -------------------------------------------

    def save_hkex(self, trade_date: str, df: pd.DataFrame) -> None:
        """Save HKEX supplement data for a specific date."""
        if df is None or df.empty:
            return
        date_dir = self._root / trade_date
        date_dir.mkdir(parents=True, exist_ok=True)
        df.to_parquet(date_dir / "hkex.parquet", index=False)
        logger.info("HKEX data saved for %s: %d rows", trade_date, len(df))

    def load_hkex(self, trade_date: str) -> pd.DataFrame:
        """Load HKEX supplement data for *trade_date*.

        Returns empty DataFrame if not found or corrupt.
        """
        hkex_path = self._root / trade_date / "hkex.parquet"
        if not hkex_path.exists():
            return pd.DataFrame()
        try:
            return pd.read_parquet(hkex_path)
        except Exception:
            logger.warning("Corrupt HKEX cache for %s", trade_date)
            return pd.DataFrame()

    def clear_old(self, keep_days: int = 30) -> int:
        """Remove cached dates older than *keep_days* calendar days.

        Returns:
            Number of directories removed.
        """
        from datetime import datetime, timedelta

        if not self._root.exists():
            return 0

        cutoff = datetime.now() - timedelta(days=keep_days)
        removed = 0
        for child in self._root.iterdir():
            if not child.is_dir():
                continue
            try:
                dt = datetime.strptime(child.name, "%Y%m%d")
                if dt < cutoff:
                    for f in child.iterdir():
                        f.unlink()
                    child.rmdir()
                    removed += 1
                    logger.info("Cache cleanup: removed %s", child.name)
            except ValueError:
                continue
        return removed

    # -- Shenwan industry mapping cache ---------------------------------

    def save_sw_mapping(self, df: pd.DataFrame) -> None:
        """Save Shenwan industry mapping to a persistent parquet file."""
        self._root.mkdir(parents=True, exist_ok=True)
        sw_path = self._root / "sw_industry_mapping.parquet"
        df.to_parquet(sw_path, index=False)
        logger.info("Shenwan mapping saved: %d rows", len(df))

    def load_sw_mapping(self, max_age_days: int = 30) -> pd.DataFrame:
        """Load cached Shenwan industry mapping if not expired.

        Args:
            max_age_days: Maximum age of the cached mapping file.

        Returns:
            DataFrame with symbol, sw_industry columns, or empty if expired/missing.
        """
        from datetime import datetime, timedelta

        sw_path = self._root / "sw_industry_mapping.parquet"
        if not sw_path.exists():
            return pd.DataFrame()

        mtime = datetime.fromtimestamp(sw_path.stat().st_mtime)
        if datetime.now() - mtime > timedelta(days=max_age_days):
            logger.info("Shenwan mapping cache expired (age=%d days)", (datetime.now() - mtime).days)
            return pd.DataFrame()

        try:
            df = pd.read_parquet(sw_path)
            logger.info("Shenwan mapping loaded from cache: %d rows", len(df))
            return df
        except Exception:
            logger.warning("Corrupt Shenwan mapping cache, ignoring")
            return pd.DataFrame()

    # -- Shenwan offline backup (survives cache expiry) ------------------

    def save_sw_backup(self, df: pd.DataFrame) -> None:
        """Save Shenwan mapping to an offline backup that never expires.

        Unlike ``save_sw_mapping`` (which has a 30-day expiry), this backup
        persists indefinitely as a fallback when the API is unavailable.
        """
        self._root.mkdir(parents=True, exist_ok=True)
        sw_backup_path = self._root / "shenwan_backup.parquet"
        df.to_parquet(sw_backup_path, index=False)
        logger.info("Shenwan backup saved: %d rows", len(df))

    def load_sw_backup(self) -> pd.DataFrame:
        """Load Shenwan mapping from offline backup (no expiry check).

        Returns:
            DataFrame with symbol, sw_industry columns, or empty if missing/corrupt.
        """
        sw_backup_path = self._root / "shenwan_backup.parquet"
        if not sw_backup_path.exists():
            return pd.DataFrame()
        try:
            df = pd.read_parquet(sw_backup_path)
            logger.info("Shenwan backup loaded: %d rows", len(df))
            return df
        except Exception:
            logger.warning("Corrupt Shenwan backup, ignoring")
            return pd.DataFrame()

    @property
    def cached_dates(self) -> list[str]:
        """Return sorted list of cached dates."""
        if not self._root.exists():
            return []
        dates = []
        for child in self._root.iterdir():
            if child.is_dir() and (child / "northbound.parquet").exists():
                dates.append(child.name)
        return sorted(dates)
