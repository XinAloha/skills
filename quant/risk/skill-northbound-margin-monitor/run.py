#!/usr/bin/env python
"""Northbound + Margin Panorama Monitor — CLI entry point.

Usage::

    python run.py                       # Latest trading day
    python run.py --date 20260630       # Specific date
    python run.py --date 20260630 --no-cache  # Force fresh data
    python run.py --top-n 30            # Top 30 in rankings

Output::

    output/YYYY-MM-DD/
        panorama_monitor_YYYYMMDD.md
        panorama_monitor_YYYYMMDD.json
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# Ensure the project root is on sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


def setup_logging(verbose: bool = False) -> None:
    """Configure logging for the monitor."""
    level = logging.DEBUG if verbose else logging.INFO
    fmt = "%(asctime)s [%(levelname)-7s] %(name)s — %(message)s"
    logging.basicConfig(level=level, format=fmt, datefmt="%Y-%m-%d %H:%M:%S")

    # Quiet down noisy third-party loggers
    for noisy in ["urllib3", "requests", "panda_data", "akshare"]:
        logging.getLogger(noisy).setLevel(logging.WARNING)


def main() -> None:
    """CLI entry point — parse args and run pipeline."""
    parser = argparse.ArgumentParser(
        description="A-share Northbound + Margin Panorama Monitor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run.py                       # Latest trading day
  python run.py --date 20260630       # Specific date
  python run.py --date 20260630 --no-cache   # Force fresh data fetch
  python run.py --top-n 30 --verbose         # Top 30, debug logging
        """.strip(),
    )
    parser.add_argument(
        "--date", type=str, default=None,
        help="Target trade date (YYYYMMDD). Default: latest trading day.",
    )
    parser.add_argument(
        "--no-cache", action="store_true",
        help="Skip cache — always fetch fresh data.",
    )
    parser.add_argument(
        "--top-n", type=int, default=20,
        help="Number of stocks in TOP-N lists (default: 20).",
    )
    parser.add_argument(
        "--output-dir", type=str, default=None,
        help="Override output directory (default: from config.json).",
    )
    parser.add_argument(
        "--summary", action="store_true",
        help="LLM summary mode: generate a shorter 150-200 word analysis.",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Enable debug-level logging.",
    )
    parser.add_argument(
        "--cleanup-cache", type=int, default=None,
        metavar="DAYS",
        help="Remove cached data older than DAYS days, then exit.",
    )

    args = parser.parse_args()
    setup_logging(args.verbose)
    logger = logging.getLogger("run")

    from core.pipeline import PanoramaPipeline

    pipeline = PanoramaPipeline()

    # --cleanup-cache mode
    if args.cleanup_cache is not None:
        removed = pipeline.cleanup_cache(keep_days=args.cleanup_cache)
        logger.info("Cache cleanup: removed %d directories older than %d days",
                     removed, args.cleanup_cache)
        print(f"Cache cleanup complete: {removed} directories removed.")
        return

    # Normal run
    logger.info("Starting panorama monitor ...")
    if args.date:
        logger.info("Target date: %s", args.date)
    else:
        logger.info("Target date: latest trading day (auto-detect)")

    use_cache = not args.no_cache
    if not use_cache:
        logger.info("Cache disabled — fetching fresh data")

    result = pipeline.run(
        trade_date=args.date,
        use_cache=use_cache,
        top_n=args.top_n,
        summary_mode=args.summary,
    )

    # Print summary
    print()
    print("=" * 60)
    print(f"  Panorama Monitor — {result.trade_date}")
    print("=" * 60)
    print(f"  Composite Score:  {result.composite_score:.0f}/100 ({result.composite_grade})")
    print(f"  Northbound:       {result.nb_triggered}/{result.nb_total} triggered")
    print(f"  Margin:           {result.margin_triggered}/{result.margin_total} triggered")
    print(f"  Resonance:        {result.resonance_triggered}/4 patterns")
    print("-" * 60)
    if result.md_path.exists():
        print(f"  Report (MD):      {result.md_path}")
    if result.json_path.exists():
        print(f"  Report (JSON):    {result.json_path}")
    if result.errors:
        print("-" * 60)
        for e in result.errors:
            print(f"  [WARN] {e}")
    print("=" * 60)
    print()

    if result.errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
