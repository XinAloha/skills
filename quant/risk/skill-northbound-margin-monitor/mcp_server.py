#!/usr/bin/env python
"""MCP server for skill-northbound-margin-monitor.

Provides 3 tools for programmatic access to the panorama monitor pipeline.

Usage::

    python mcp_server.py              # stdio transport (default)
    python mcp_server.py --sse        # SSE transport (for remote clients)
    python mcp_server.py --port 8765  # SSE on custom port

Tools::

    run_panorama       — Run the full panorama pipeline
    get_latest_report  — Read the most recent report
    check_trading_day  — Check if a date is an A-share trading day
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# Ensure project root is on sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# MCP server setup
# ------------------------------------------------------------------

def _build_server():
    """Build and return the MCP server instance."""
    try:
        from mcp.server import Server
        from mcp.server.stdio import stdio_server
        from mcp.types import Tool, TextContent
    except ImportError:
        raise RuntimeError(
            "mcp package not installed. Install with: pip install mcp>=1.0.0"
        )

    server = Server("northbound-margin-monitor")

    # ------------------------------------------------------------------
    # Tool: run_panorama
    # ------------------------------------------------------------------

    @server.tool()
    async def run_panorama(
        date: Optional[str] = None,
        use_cache: bool = True,
        top_n: int = 20,
    ) -> str:
        """Run the northbound + margin panorama pipeline for a trading day.

        Generates Markdown and JSON reports in the output directory.

        Args:
            date: Target trade date in YYYYMMDD format. Default: latest trading day.
            use_cache: Use cached data when available. Set false to force fresh fetch.
            top_n: Number of stocks in TOP-N ranking lists (default 20).

        Returns:
            JSON string with pipeline result summary and report paths.
        """
        from core.pipeline import PanoramaPipeline

        pipeline = PanoramaPipeline()
        result = pipeline.run(trade_date=date, use_cache=use_cache, top_n=top_n)

        summary = {
            "trade_date": result.trade_date,
            "composite_score": result.composite_score,
            "composite_grade": result.composite_grade,
            "northbound_triggered": result.nb_triggered,
            "margin_triggered": result.margin_triggered,
            "resonance_triggered": result.resonance_triggered,
            "report_md": str(result.md_path) if result.md_path.exists() else "",
            "report_json": str(result.json_path) if result.json_path.exists() else "",
            "errors": result.errors,
        }
        return json.dumps(summary, ensure_ascii=False, indent=2)

    # ------------------------------------------------------------------
    # Tool: get_latest_report
    # ------------------------------------------------------------------

    @server.tool()
    async def get_latest_report(
        date: Optional[str] = None,
        format: str = "summary",
    ) -> str:
        """Read the most recent panorama report.

        Args:
            date: Specific report date in YYYYMMDD. Default: most recent available.
            format: "summary" (JSON) or "full" (Markdown). Default: summary.

        Returns:
            Report content as string.
        """
        output_dir = _PROJECT_ROOT / "output"

        if not output_dir.exists():
            return json.dumps({"error": "No output directory found. Run the pipeline first."})

        # Find report by date
        if date:
            dt = datetime.strptime(date, "%Y%m%d")
            date_dir_name = dt.strftime("%Y-%m-%d")
            report_dir = output_dir / date_dir_name
        else:
            # Find the most recent date directory
            dirs = sorted(
                [d for d in output_dir.iterdir() if d.is_dir()],
                reverse=True,
            )
            if not dirs:
                return json.dumps({"error": "No reports found."})
            report_dir = dirs[0]

        if not report_dir.exists():
            return json.dumps({"error": f"No report for date: {date or 'latest'}"})

        if format == "full":
            md_files = list(report_dir.glob("*.md"))
            if not md_files:
                return json.dumps({"error": f"No Markdown report in {report_dir}"})
            content = md_files[0].read_text(encoding="utf-8")
            return content

        # Default: return JSON summary
        json_files = list(report_dir.glob("*.json"))
        if not json_files:
            return json.dumps({"error": f"No JSON report in {report_dir}"})

        json_data = json.loads(json_files[0].read_text(encoding="utf-8"))

        # Return a compact summary
        summary = {
            "report_date": json_data.get("meta", {}).get("trade_date"),
            "fetch_time": json_data.get("meta", {}).get("fetch_time"),
            "composite": json_data.get("composite", {}),
            "northbound": {
                "triggered": json_data["northbound"].get("triggered_count", 0),
                "bullish": json_data["northbound"].get("bullish_count", 0),
                "bearish": json_data["northbound"].get("bearish_count", 0),
            },
            "margin": {
                "triggered": json_data["margin"].get("triggered_count", 0),
                "bullish": json_data["margin"].get("bullish_count", 0),
                "bearish": json_data["margin"].get("bearish_count", 0),
            },
            "resonance": {
                "triggered": json_data["resonance"].get("triggered_count", 0),
            },
            "provenance": json_data.get("provenance", {}),
        }
        return json.dumps(summary, ensure_ascii=False, indent=2)

    # ------------------------------------------------------------------
    # Tool: check_trading_day
    # ------------------------------------------------------------------

    @server.tool()
    async def check_trading_day(date: str) -> str:
        """Check if a date is an A-share trading day.

        Args:
            date: Date in YYYYMMDD format.

        Returns:
            JSON with trading day status and last trade date.
        """
        from core.data_fetcher import DataFetcher

        fetcher = DataFetcher()
        result = {"date": date, "is_trading_day": False, "error": ""}

        try:
            fetcher.init_api()
            result["is_trading_day"] = fetcher.is_trading_day(date)
            result["last_trade_date"] = fetcher.get_last_trade_date()
        except Exception as e:
            result["error"] = str(e)

        return json.dumps(result, ensure_ascii=False)

    return server


# ------------------------------------------------------------------
# Entry point
# ------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="MCP server for northbound-margin-monitor",
    )
    parser.add_argument(
        "--sse", action="store_true",
        help="Use SSE transport instead of stdio.",
    )
    parser.add_argument(
        "--port", type=int, default=8765,
        help="Port for SSE transport (default: 8765).",
    )
    parser.add_argument(
        "--host", type=str, default="127.0.0.1",
        help="Host for SSE transport (default: 127.0.0.1).",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    server = _build_server()

    if args.sse:
        import asyncio
        from mcp.server.sse import SseServerTransport
        from starlette.applications import Starlette
        from starlette.routing import Route
        import uvicorn

        sse = SseServerTransport("/messages/")

        async def handle_sse(request):
            async with sse.connect_sse(
                request.scope, request.receive, request._send
            ) as streams:
                await server.run(
                    streams[0], streams[1], server.create_initialization_options()
                )

        async def handle_messages(request):
            await sse.handle_post_message(
                request.scope, request.receive, request._send
            )

        app = Starlette(
            routes=[
                Route("/sse", endpoint=handle_sse),
                Route("/messages/", endpoint=handle_messages, methods=["POST"]),
            ]
        )

        print(f"MCP SSE server starting on http://{args.host}:{args.port}/sse")
        uvicorn.run(app, host=args.host, port=args.port)
    else:
        import asyncio
        from mcp.server.stdio import stdio_server

        async def _run_stdio():
            async with stdio_server() as (read_stream, write_stream):
                await server.run(
                    read_stream, write_stream, server.create_initialization_options()
                )

        asyncio.run(_run_stdio())


if __name__ == "__main__":
    main()
