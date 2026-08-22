"""Panorama pipeline: orchestrates data fetch → analysis → report generation.

Usage::

    from core.pipeline import PanoramaPipeline

    pipeline = PanoramaPipeline()
    result = pipeline.run()  # latest trading day
    result = pipeline.run(trade_date="20260630")
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from .cache import CacheManager
from .data_fetcher import DataFetcher
from .northbound import (
    run_all_detectors as run_nb_detectors,
    compute_composite_score as nb_composite_score,
    get_triggered_signals as nb_triggered,
    get_bullish_signals as nb_bullish,
    get_bearish_signals as nb_bearish,
)
from .margin import (
    run_all_detectors as run_margin_detectors,
    compute_composite_score as margin_composite_score,
    get_triggered_signals as mg_triggered,
    get_bullish_signals as mg_bullish,
    get_bearish_signals as mg_bearish,
)
from .futures import (
    run_all_detectors as run_futures_detectors,
    compute_composite_score as futures_composite_score,
    get_triggered_signals as futures_triggered,
    get_bullish_signals as futures_bullish,
    get_bearish_signals as futures_bearish,
)
from .resonance import (
    analyse_resonance,
    get_triggered_patterns,
    compute_resonance_score,
)
from .price_volume import (
    run_all_detectors as run_pv_detectors,
    compute_composite_score as pv_composite_score,
    get_triggered_signals as pv_triggered,
    get_bullish_signals as pv_bullish,
    get_bearish_signals as pv_bearish,
)
from .microstructure import (
    run_all_detectors as run_micro_detectors,
    compute_composite_score as micro_composite_score,
    get_triggered_signals as micro_triggered,
    get_bullish_signals as micro_bullish,
    get_bearish_signals as micro_bearish,
)
from .scorer import (
    compute_capital_flow_score,
    compute_industry_neutral_ranking,
    compute_risk_level,
    rank_stocks_by_margin_balance,
    rank_stocks_by_margin_buy,
)
from .reporter import (
    _find_previous_report,
    generate_markdown_report,
    generate_json_output,
    write_report,
)

try:
    from llm.analyst import LLMAnalyst as _LLMAnalyst
    _LLM_AVAILABLE = True
except ImportError:
    _LLM_AVAILABLE = False

logger = logging.getLogger(__name__)


def _merge_hkex_supplement(
    nb_summary: pd.DataFrame, hkex_df: pd.DataFrame
) -> pd.DataFrame:
    """Fill NaN ``net_buy_amount`` values in nb_summary with HKEX-derived net.

    Only fills gaps — does not overwrite valid existing data.
    Marks filled rows with ``_hkex_filled`` flag column.
    """
    if hkex_df.empty or "date" not in hkex_df.columns:
        return nb_summary

    if "nb_net_rmb" not in hkex_df.columns:
        return nb_summary

    df = nb_summary.copy()
    hkex_map = {}
    for _, row in hkex_df.iterrows():
        d = row["date"]
        net = row["nb_net_rmb"]
        if pd.notna(net):
            hkex_map[d] = net

    if "net_buy_amount" not in df.columns:
        df["net_buy_amount"] = np.nan

    df["_hkex_filled"] = False
    for idx, row in df.iterrows():
        date_str = row["date"]
        if date_str in hkex_map:
            existing = row.get("net_buy_amount", np.nan)
            if pd.isna(existing) or existing == 0:
                df.at[idx, "net_buy_amount"] = hkex_map[date_str]
                df.at[idx, "_hkex_filled"] = True

    filled = df["_hkex_filled"].sum()
    if filled > 0:
        logger.info(
            "HKEX supplement filled %d NaN net_buy_amount values", filled
        )
    return df


@dataclass
class PipelineResult:
    """Result of a pipeline run."""
    trade_date: str
    md_path: Path
    json_path: Path
    composite_score: float
    composite_grade: str
    nb_triggered: int
    nb_total: int
    margin_triggered: int
    margin_total: int
    resonance_triggered: int
    futures_triggered: int = 0
    pv_triggered: int = 0
    micro_triggered: int = 0
    llm_analysis: str = ""
    llm_source: str = "none"
    errors: list[str] = field(default_factory=list)


class PanoramaPipeline:
    """Full panorama pipeline: fetch → analyse → report."""

    def __init__(self, config: Optional[dict] = None, cache_root: str | Path = "cache"):
        import json as _json

        self._config = config
        if self._config is None:
            cfg_path = Path(__file__).resolve().parent.parent / "config.json"
            if cfg_path.exists():
                self._config = _json.loads(cfg_path.read_text(encoding="utf-8"))
            else:
                self._config = {}

        self._fetcher = DataFetcher(config=self._config)
        self._cache = CacheManager(cache_root=cache_root)
        self._errors: list[str] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def cleanup_cache(self, keep_days: int = 30) -> int:
        """Remove cached data older than *keep_days*.

        Returns:
            Number of directories removed.
        """
        return self._cache.clear_old(keep_days=keep_days)

    def run(
        self,
        trade_date: Optional[str] = None,
        use_cache: bool = True,
        top_n: int = 20,
        summary_mode: bool = False,
    ) -> PipelineResult:
        """Execute the full panorama pipeline.

        Args:
            trade_date: Target trading day (YYYYMMDD). Default: latest.
            use_cache: If True, use cached data when available.
            top_n: Number of stocks in TOP-N lists.
            summary_mode: If True, LLM generates a short 150-200 word summary.

        Returns:
            PipelineResult with output paths and summary stats.
        """
        self._errors.clear()

        # 1. Resolve trade date
        if trade_date is None:
            try:
                self._fetcher.init_api()
                trade_date = self._fetcher.get_last_trade_date()
                logger.info("Using latest trade date: %s", trade_date)
            except Exception as e:
                logger.error("Cannot determine latest trade date: %s", e)
                self._errors.append(f"Date resolution failed: {e}")
                return self._empty_result("unknown")

        logger.info("=" * 60)
        logger.info("PanoramaPipeline starting for %s", trade_date)
        logger.info("=" * 60)

        # 2. Check cache
        if use_cache and self._cache.has(trade_date):
            logger.info("Cache hit for %s — loading cached data", trade_date)
            nb_summary, margin_macro, margin_detail, stock_info, futures_data = self._cache.load(trade_date)
            nb_flow = self._cache.load_nb_flow(trade_date)
            hkex_data = self._cache.load_hkex(trade_date)
            universe = pd.DataFrame()
            fetch_time = self._cache.load_meta(trade_date).get("fetch_time", "cached")

            # Enrich cached stock_info with Shenwan mapping if missing
            if not stock_info.empty and "sw_industry" not in stock_info.columns:
                sw_mapping = self._cache.load_sw_mapping()
                if not sw_mapping.empty:
                    stock_info = stock_info.merge(sw_mapping, on="symbol", how="left")
                    if "industry" in stock_info.columns:
                        stock_info["sw_industry"] = stock_info["sw_industry"].fillna(stock_info["industry"])
                    logger.info("Enriched cached stock_info with Shenwan mapping")
        else:
            # 3. Fetch all data
            try:
                self._fetcher.init_api()
            except Exception as e:
                logger.warning("Pandadata init failed (non-fatal): %s", e)
                self._errors.append(f"Pandadata init: {e}")

            try:
                data = self._fetcher.fetch_all_data(trade_date)
                nb_summary = data["northbound_summary"]
                nb_flow = data["northbound_flow"]
                margin_detail = data["margin_detail"]
                margin_macro = data["margin_macro"]
                futures_data = data.get("futures_data", pd.DataFrame())
                hkex_data = data.get("hkex_data", pd.DataFrame())
                stock_info = data["stock_info"]
                universe = data["universe"]
                fetch_time = data["fetch_time"]
            except Exception as e:
                logger.error("Data fetch failed: %s", e)
                self._errors.append(f"Data fetch: {e}")
                return self._empty_result(trade_date)

            # 4. Save to cache
            if use_cache:
                try:
                    self._cache.save(
                        trade_date,
                        nb_summary,
                        margin_macro,
                        margin_detail,
                        stock_info,
                        northbound_flow_df=nb_flow,
                        futures_df=futures_data,
                        fetch_time=fetch_time,
                    )
                    # Save HKEX supplement if available
                    if hkex_data is not None and not hkex_data.empty:
                        self._cache.save_hkex(trade_date, hkex_data)
                except Exception as e:
                    logger.warning("Cache save failed (non-fatal): %s", e)

        # 4.5. Merge HKEX supplement to fill NaN net_buy_amount gaps
        if hkex_data is not None and not hkex_data.empty and not nb_summary.empty:
            nb_summary = _merge_hkex_supplement(nb_summary, hkex_data)

        # 4.6. Accumulate flow direction history
        nb_flow_history = pd.DataFrame()
        try:
            from .flow_accumulator import FlowAccumulator
            flow_acc = FlowAccumulator(cache_root=self._cache._root)
            nb_flow_history = flow_acc.accumulate(trade_date, nb_flow)
            # Also provide direction series for detectors
            nb_dir_series = flow_acc.get_direction_series(aggregate="daily")
            if not nb_dir_series.empty:
                logger.info("Flow direction history: %d dates", len(nb_dir_series))
        except Exception as e:
            logger.warning("Flow accumulator failed (non-fatal): %s", e)
            nb_dir_series = pd.DataFrame()

        # 5. Run northbound detectors
        logger.info("Running northbound detectors ...")
        nb_signals = run_nb_detectors(
            nb_summary, nb_flow, stock_info, self._config,
            nb_flow_history=nb_dir_series,
        )
        nb_composite = nb_composite_score(nb_signals)

        # 6. Run margin detectors
        logger.info("Running margin detectors ...")
        margin_signals = run_margin_detectors(
            margin_detail, margin_macro, stock_info, self._config,
        )
        margin_composite = margin_composite_score(margin_signals)

        # 6.5. Run futures detectors (3rd dimension)
        logger.info("Running futures detectors ...")
        futures_signals = run_futures_detectors(
            futures_data, self._config,
        )
        futures_composite = futures_composite_score(futures_signals)

        # 6.6. Run price-volume detectors (4th dimension — confirmation)
        logger.info("Running price-volume detectors ...")
        pv_signals = run_pv_detectors(
            nb_summary, self._config,
        )
        pv_composite = pv_composite_score(pv_signals)

        # 6.7. Run microstructure detectors (5th dimension — breadth/liquidity)
        logger.info("Running microstructure detectors ...")
        micro_signals = run_micro_detectors(
            nb_flow, futures_data, margin_macro, self._config,
        )
        micro_composite = micro_composite_score(micro_signals)

        # 7. Resonance analysis
        logger.info("Running resonance analysis ...")
        resonance_results = analyse_resonance(
            nb_composite,
            margin_composite,
            sum(1 for s in nb_signals if s.direction == "bullish"),
            sum(1 for s in nb_signals if s.direction == "bearish"),
            sum(1 for s in margin_signals if s.direction == "bullish"),
            sum(1 for s in margin_signals if s.direction == "bearish"),
            self._config,
        )
        resonance_score = compute_resonance_score(resonance_results, self._config)

        # 8. Composite scoring
        logger.info("Computing composite score ...")
        max_possible = (len(nb_signals) + len(margin_signals)
                        + len(futures_signals) + len(pv_signals)
                        + len(micro_signals))

        # Compute NB data quality: fraction of signals using real (non-proxy) data
        nb_proxy_sources = {"csi300_proxy", "market_value_diff"}
        nb_proxy_count = sum(
            1 for s in nb_signals
            if s.detail.get("data_source", "") in nb_proxy_sources
        )
        nb_data_quality = 1.0 - (nb_proxy_count / max(1, len(nb_signals)))
        if nb_data_quality < 0.5:
            logger.warning(
                "Northbound data quality degraded (%.0f%% proxy), "
                "NB weight auto-reduced", nb_proxy_count / max(1, len(nb_signals)) * 100
            )

        composite = compute_capital_flow_score(
            nb_composite,
            margin_composite,
            resonance_score,
            sum(1 for s in nb_signals if s.triggered),
            sum(1 for s in margin_signals if s.triggered),
            sum(1 for r in resonance_results if r.triggered),
            self._config,
            futures_composite=futures_composite,
            futures_triggered_count=sum(1 for s in futures_signals if s.triggered),
            pv_composite=pv_composite,
            pv_triggered_count=sum(1 for s in pv_signals if s.triggered),
            micro_composite=micro_composite,
            micro_triggered_count=sum(1 for s in micro_signals if s.triggered),
            max_possible=max_possible,
            nb_data_quality=nb_data_quality,
        )

        # 9. Stock rankings
        logger.info("Ranking stocks ...")
        top_bal = rank_stocks_by_margin_balance(margin_detail, stock_info, top_n)
        top_buy = rank_stocks_by_margin_buy(margin_detail, stock_info, top_n)

        # 9.1. Industry-neutral sector ranking
        industry_ranking = compute_industry_neutral_ranking(margin_detail, stock_info, top_n=10)

        # 9.2. Comprehensive risk level
        logger.info("Computing risk level ...")
        risk_level = compute_risk_level(
            nb_signals, margin_signals, futures_signals, resonance_results,
            pv_signals=pv_signals,
            micro_signals=micro_signals,
            margin_macro=margin_macro,
            config=self._config,
        )

        # 9.5. LLM macro analysis
        llm_analysis = ""
        llm_source = "none"
        llm_model = ""
        if _LLM_AVAILABLE:
            logger.info("Running LLM macro analysis ...")
            try:
                # Extract macro summary data for prompt
                mg_bal_亿 = 0.0
                mg_short_億 = 0.0
                mg_buy_億 = 0.0
                if not margin_macro.empty:
                    date_col = "date" if "date" in margin_macro.columns else "日期"
                    if date_col in margin_macro.columns:
                        latest_date = margin_macro[date_col].max()
                        latest_data = margin_macro[margin_macro[date_col] == latest_date]
                    else:
                        latest_data = margin_macro
                    for col in ["margin_balance", "融资余额"]:
                        if col in latest_data.columns:
                            mg_bal_亿 = pd.to_numeric(latest_data[col], errors="coerce").sum() / 1e8
                            break
                    for col in ["short_balance", "融券余额"]:
                        if col in latest_data.columns:
                            mg_short_億 = pd.to_numeric(latest_data[col], errors="coerce").sum() / 1e8
                            break
                    for col in ["buy_on_margin_value", "融资买入额"]:
                        if col in latest_data.columns:
                            mg_buy_億 = pd.to_numeric(latest_data[col], errors="coerce").sum() / 1e8
                            break

                top_industries = []
                if not stock_info.empty and "industry" in stock_info.columns:
                    top_industries = stock_info["industry"].value_counts().head(5).index.tolist()

                llm = _LLMAnalyst(config=self._config)
                llm_analysis, llm_source, llm_model = llm.analyze(
                    composite_score=composite.score,
                    composite_grade=composite.grade,
                    composite_label=composite.label,
                    composite_summary=composite.summary,
                    nb_signals=nb_signals,
                    margin_signals=margin_signals,
                    futures_signals=futures_signals,
                    resonance_results=resonance_results,
                    margin_balance_亿=mg_bal_亿,
                    short_balance_亿=mg_short_億,
                    margin_buy_億=mg_buy_億,
                    top_industries=top_industries,
                    summary_mode=summary_mode,
                )
                logger.info("LLM analysis: model=%s, source=%s, length=%d chars", llm_model, llm_source, len(llm_analysis))
            except Exception as e:
                logger.warning("LLM analysis failed: %s", e)
                llm_analysis = f"（LLM 分析不可用: {e}）"
                llm_source = "error"
                llm_model = ""
        else:
            logger.info("LLM module not available — skipping macro analysis")

        # 10. Find previous report for historical comparison
        logger.info("Looking for previous report ...")
        output_dir = self._config.get("output", {}).get("dir", "output")
        previous_report = _find_previous_report(trade_date, output_dir)

        # 10. Generate reports
        logger.info("Generating reports ...")
        markdown = generate_markdown_report(
            trade_date=trade_date,
            nb_signals=nb_signals,
            margin_signals=margin_signals,
            futures_signals=futures_signals,
            resonance_results=resonance_results,
            composite=composite,
            nb_summary=nb_summary,
            margin_detail=margin_detail,
            margin_macro=margin_macro,
            futures_data=futures_data,
            top_margin_balance=top_bal,
            top_margin_buy=top_buy,
            stock_info=stock_info,
            industry_ranking=industry_ranking,
            fetch_time=fetch_time,
            config=self._config,
            llm_analysis=llm_analysis,
            llm_source=llm_source,
            llm_model=llm_model,
            previous_report=previous_report,
            pv_signals=pv_signals,
            micro_signals=micro_signals,
            risk_level=risk_level,
        )

        json_data = generate_json_output(
            trade_date=trade_date,
            nb_signals=nb_signals,
            margin_signals=margin_signals,
            futures_signals=futures_signals,
            resonance_results=resonance_results,
            composite=composite,
            top_margin_balance=top_bal,
            top_margin_buy=top_buy,
            fetch_time=fetch_time,
            nb_summary=nb_summary,
            margin_detail=margin_detail,
            margin_macro=margin_macro,
            futures_data=futures_data,
            stock_info=stock_info,
            industry_ranking=industry_ranking,
            config=self._config,
            llm_analysis=llm_analysis,
            llm_source=llm_source,
            llm_model=llm_model,
            previous_report=previous_report,
            pv_signals=pv_signals,
            micro_signals=micro_signals,
            risk_level=risk_level,
        )

        md_path, json_path = write_report(
            trade_date, markdown, json_data, config=self._config,
        )

        # 11. Validate reports
        self._validate_reports(md_path, json_path)

        # 12. Result
        n_triggered = sum(1 for s in nb_signals if s.triggered)
        m_triggered = sum(1 for s in margin_signals if s.triggered)
        f_triggered = sum(1 for s in futures_signals if s.triggered)
        r_triggered = sum(1 for r in resonance_results if r.triggered)
        pv_triggered_count = sum(1 for s in pv_signals if s.triggered)
        micro_triggered_count = sum(1 for s in micro_signals if s.triggered)

        logger.info("=" * 60)
        logger.info(
            "Pipeline complete: score=%.0f (%s), nb=%d, margin=%d, futures=%d, pv=%d, micro=%d, resonance=%d, llm=%s",
            composite.score, composite.grade,
            n_triggered, m_triggered, f_triggered, pv_triggered_count, micro_triggered_count, r_triggered, llm_source,
        )
        logger.info("Markdown: %s", md_path)
        logger.info("JSON:     %s", json_path)
        if self._errors:
            logger.warning("Errors: %s", self._errors)
        logger.info("=" * 60)

        return PipelineResult(
            trade_date=trade_date,
            md_path=md_path,
            json_path=json_path,
            composite_score=composite.score,
            composite_grade=composite.grade,
            nb_triggered=n_triggered,
            nb_total=len(nb_signals),
            margin_triggered=m_triggered,
            margin_total=len(margin_signals),
            futures_triggered=f_triggered,
            pv_triggered=pv_triggered_count,
            micro_triggered=micro_triggered_count,
            resonance_triggered=r_triggered,
            llm_analysis=llm_analysis,
            llm_source=llm_source,
            errors=list(self._errors),
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _validate_reports(self, md_path: Path, json_path: Path) -> None:
        """Run post-generation validation on the reports.

        Issues are logged as warnings so they don't block pipeline completion,
        but are visible in the log output for manual review.
        """
        try:
            from scripts.validate_report import validate_md, validate_json
        except ImportError:
            return  # validation script not importable — skip silently

        issues: list[str] = []
        try:
            md_text = md_path.read_text(encoding="utf-8-sig")
            issues.extend(validate_md(md_text))
        except Exception as e:
            logger.warning("Report validation: cannot read markdown — %s", e)

        try:
            import json
            json_data = json.loads(json_path.read_text(encoding="utf-8-sig"))
            issues.extend(validate_json(json_data))
        except Exception as e:
            logger.warning("Report validation: cannot read JSON — %s", e)

        if issues:
            logger.warning("Report validation found %d issue(s):", len(issues))
            for issue in issues[:10]:  # Cap to avoid log spam
                logger.warning("  - %s", issue)
            if len(issues) > 10:
                logger.warning("  ... and %d more", len(issues) - 10)
        else:
            logger.info("Report validation: OK")

    def _empty_result(self, trade_date: str) -> PipelineResult:
        return PipelineResult(
            trade_date=trade_date,
            md_path=Path(""),
            json_path=Path(""),
            composite_score=0.0,
            composite_grade="N/A",
            nb_triggered=0,
            nb_total=0,
            margin_triggered=0,
            margin_total=0,
            resonance_triggered=0,
            errors=list(self._errors),
        )
