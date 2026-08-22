#!/usr/bin/env python3
"""
Framework-neutral paper replication pipeline.

Primary flow:
    search paper -> download/extract PDF -> run standalone reproduction ->
    package reports, metrics, CSV data, and charts.

Examples:
    python run_research.py --pipeline --paper "momentum portfolio" --symbols rb,if,au
    python run_research.py --pdf paper.pdf --strategy tsmom --symbols rb,if,au
    python run_research.py --paper-id 2201.06635 --symbols rb,HC,AU --strategy tsmom

Output root:
    /home/coder/project/replication/paper-replication
"""

import argparse
import json
import os
import subprocess
import sys
import time


# Path to this script's directory
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(SCRIPT_DIR)

# Fixed Linux project output directory.
PROJECT_DIR = "/home/coder/project/replication/paper-replication"


def ensure_dirs(paper_id=None):
    """Ensure output directories exist for a paper."""
    if paper_id:
        base_dir = os.path.join(PROJECT_DIR, paper_id.replace("/", "_"))
    else:
        base_dir = os.path.join(PROJECT_DIR, "default")
    os.makedirs(base_dir, exist_ok=True)
    for subdir in ["strategies", "reports", "data", "charts"]:
        os.makedirs(os.path.join(base_dir, subdir), exist_ok=True)
    return base_dir


def run_step(name, cmd, check=True):
    """Run a subprocess step with logging."""
    print(f"\n{'=' * 60}")
    print(f"  STEP: {name}")
    print(f"  CMD:  {' '.join(cmd)}")
    print(f"{'=' * 60}")

    start = time.time()
    result = subprocess.run(cmd, capture_output=False, text=True)
    elapsed = time.time() - start

    status = "OK" if result.returncode == 0 else f"FAIL (exit {result.returncode})"
    print(f"\n[{status}] {name} completed in {elapsed:.1f}s")
    return result


def search_and_download(query, max_results=5, output_dir=None):
    """Search arxiv and download the top result."""
    if output_dir is None:
        output_dir = os.path.join(PROJECT_DIR, "downloads")
    os.makedirs(output_dir, exist_ok=True)

    search_cmd = [
        sys.executable, os.path.join(SCRIPT_DIR, "search_arxiv.py"),
        query, "--max", str(max_results), "--download",
        "--output-dir", output_dir,
    ]
    result = run_step(f"Search arxiv: '{query}'", search_cmd)
    return result.returncode == 0


def extract_paper(pdf_path, output_dir):
    """Extract paper content."""
    md_path = os.path.join(output_dir, "reports",
                          f"extracted_{os.path.basename(pdf_path).replace('.pdf', '.md')}")
    extract_cmd = [
        sys.executable, os.path.join(SCRIPT_DIR, "extract_paper.py"),
        "--pdf", pdf_path, "--markdown", "--output", md_path,
    ]
    result = run_step(f"Extract: {pdf_path}", extract_cmd)
    return md_path if result.returncode == 0 else None


def reproduce(symbols, strategy="tsmom", start="2020-01-01", end="2024-12-31",
              target_vol=0.10, output_dir=None):
    """Run the reproduction backtest."""
    symbols_str = ",".join(symbols)
    reproduce_cmd = [
        sys.executable, os.path.join(SCRIPT_DIR, "reproduce_paper.py"),
        "--symbols", symbols_str,
        "--strategy", strategy,
        "--start", start,
        "--end", end,
        "--target-vol", str(target_vol),
        "--output-dir", output_dir,
    ]
    result = run_step(f"Reproduce: {strategy} on {symbols_str}", reproduce_cmd)
    return result.returncode == 0


def organize_outputs(strategy, output_dir):
    """Move output files to proper subdirectories."""
    import shutil

    data_dir = os.path.join(output_dir, "data")
    charts_dir = os.path.join(output_dir, "charts")
    reports_dir = os.path.join(output_dir, "reports")

    # Move equity/weights to data/
    for filename in ["equity", "weights"]:
        src = os.path.join(output_dir, f"{filename}_{strategy}.csv")
        dst = os.path.join(data_dir, f"{filename}_{strategy}.csv")
        if os.path.exists(src):
            shutil.move(src, dst)
            print(f"  [moved] {filename}_{strategy}.csv -> data/")

    # Move chart to charts/
    chart_src = os.path.join(output_dir, f"chart_{strategy}.png")
    chart_dst = os.path.join(charts_dir, f"chart_{strategy}.png")
    if os.path.exists(chart_src):
        shutil.move(chart_src, chart_dst)
        print(f"  [moved] chart_{strategy}.png -> charts/")

    # Move metrics to reports/
    metrics_src = os.path.join(output_dir, f"metrics_{strategy}.json")
    metrics_dst = os.path.join(reports_dir, f"metrics_{strategy}.json")
    if os.path.exists(metrics_src):
        shutil.move(metrics_src, metrics_dst)
        print(f"  [moved] metrics_{strategy}.json -> reports/")


def full_pipeline(args):
    """Run the complete research-to-trade pipeline."""
    if args.paper_id:
        paper_id = args.paper_id
    elif args.paper:
        paper_id = args.paper.replace(" ", "_")[:30]
    elif args.pdf:
        paper_id = os.path.splitext(os.path.basename(args.pdf))[0][:30]
    else:
        paper_id = "default"
    output_dir = ensure_dirs(paper_id)

    print("=" * 60)
    print("  PAPER REPLICATION 鈥?FULL PIPELINE")
    print("=" * 60)
    print(f"  Paper ID:       {paper_id}")
    print(f"  Symbols:        {args.symbols}")
    print(f"  Strategy:       {args.strategy}")
    print(f"  Period:         {args.start} 鈫?{args.end}")
    print(f"  Target Vol:     {args.target_vol}")
    print(f"  Output:         {output_dir}")
    print("=" * 60)

    symbols = [s.strip() for s in args.symbols.split(",")]
    pdf_path = None

    # Phase 1: Get the paper
    if args.pdf:
        pdf_path = args.pdf
        print(f"[*] Phase 1: Using provided PDF: {pdf_path}")
        # Copy PDF to reports/
        import shutil
        dst = os.path.join(output_dir, "reports", os.path.basename(pdf_path))
        shutil.copy2(pdf_path, dst)
        pdf_path = dst
    elif args.paper_id:
        # Download specific paper
        pdf_path = os.path.join(output_dir, "reports",
                               f"{args.paper_id.replace('/', '_')}.pdf")
        if not os.path.exists(pdf_path):
            print(f"[*] Phase 1: Downloading arxiv paper {args.paper_id}...")
            import urllib.request
            url = f"https://arxiv.org/pdf/{args.paper_id}.pdf"
            try:
                urllib.request.urlretrieve(url, pdf_path)
                print(f"[OK] Downloaded: {pdf_path}")
            except Exception as e:
                print(f"[ERROR] Download failed: {e}")
                return
        else:
            print(f"[*] Phase 1: Paper already downloaded: {pdf_path}")
    elif args.paper:
        print(f"[*] Phase 1: Searching for papers matching '{args.paper}'...")
        search_and_download(args.paper, max_results=3)
        # Find the first downloaded PDF
        download_dir = os.path.join(PROJECT_DIR, "downloads")
        pdfs = [f for f in os.listdir(download_dir) if f.endswith(".pdf")]
        if pdfs:
            src = os.path.join(download_dir, pdfs[0])
            dst = os.path.join(output_dir, "reports", pdfs[0])
            import shutil
            shutil.move(src, dst)
            pdf_path = dst
        else:
            print("[ERROR] No PDF found. Search returned no results.")
            return

    if not pdf_path or not os.path.exists(pdf_path):
        print("[ERROR] No paper PDF available.")
        return

    # Phase 2: Extract paper content
    print(f"\n[*] Phase 2: Extracting content from {pdf_path}...")
    extracted_md = extract_paper(pdf_path, output_dir)
    if extracted_md:
        print(f"[OK] Extraction saved to: {extracted_md}")

    # Phase 3: Reproduce
    if not args.skip_reproduce:
        print(f"\n[*] Phase 3: Reproducing strategy '{args.strategy}'...")
        success = reproduce(symbols, args.strategy, args.start, args.end,
                           args.target_vol, output_dir)
        if success:
            organize_outputs(args.strategy, output_dir)
        else:
            print("[WARN] Reproduction may have issues. Check output above.")

    # Phase 4: Summary
    print(f"\n{'=' * 60}")
    print(f"  PIPELINE COMPLETE")
    print(f"{'=' * 60}")
    print(f"  Project directory: {output_dir}")
    print(f"  Files generated:")
    for root, dirs, files in os.walk(output_dir):
        for f in sorted(files):
            filepath = os.path.join(root, f)
            relpath = os.path.relpath(filepath, output_dir)
            size = os.path.getsize(filepath)
            print(f"    {relpath:<45s} {size:>10,} bytes")

    print(f"\n  Next steps:")
    print(f"    1. Review extracted paper: reports/extracted_*.md")
    print(f"    2. Check reproduction metrics: reports/metrics_*.json")
    print(f"    3. Review charts and exported CSV files")
    print(f"    4. Document data-source and metric gaps against the paper")


def main():
    parser = argparse.ArgumentParser(
        description="Paper Replication Pipeline - standalone research reproduction",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full pipeline from search to strategy
  python run_research.py --pipeline --paper "momentum portfolio" --symbols rb,if,au

  # From specific arxiv paper
  python run_research.py --pipeline --paper-id 2201.06635 --symbols rb,HC,AU

  # From existing PDF
  python run_research.py --pdf paper.pdf --strategy tsmom --symbols rb,if

  # Just reproduce, skip search
  python run_research.py --symbols rb,if,au --strategy risk_parity --skip-reproduce
""",
    )

    # Paper input (one of these)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--paper", help="Search query for arxiv papers")
    group.add_argument("--paper-id", help="Specific arxiv paper ID (e.g., 2201.06635)")
    group.add_argument("--pdf", help="Path to existing PDF file")

    # Pipeline control
    parser.add_argument("--pipeline", action="store_true", help="Run full pipeline")
    parser.add_argument("--symbols", default="rb,if,au", help="Comma-separated futures symbols")
    parser.add_argument("--strategy", default="tsmom",
                       choices=["tsmom", "csmom", "risk_parity", "trend_vol"],
                       help="Strategy type")
    parser.add_argument("--start", default="2020-01-01", help="Backtest start date")
    parser.add_argument("--end", default="2024-12-31", help="Backtest end date")
    parser.add_argument("--target-vol", type=float, default=0.10, help="Target annual volatility")
    parser.add_argument("--skip-reproduce", action="store_true", help="Skip reproduction step")

    args = parser.parse_args()

    if not (args.paper or args.paper_id or args.pdf):
        print("[ERROR] Please specify --paper, --paper-id, or --pdf")
        parser.print_help()
        sys.exit(1)

    if not args.pipeline:
        # Run specific step
        if args.paper or args.paper_id:
            output_dir = ensure_dirs(args.paper_id or args.paper[:30])
            if args.paper_id:
                pdf_path = os.path.join(output_dir, "reports",
                                       f"{args.paper_id.replace('/', '_')}.pdf")
                if not os.path.exists(pdf_path):
                    import urllib.request
                    url = f"https://arxiv.org/pdf/{args.paper_id}.pdf"
                    try:
                        urllib.request.urlretrieve(url, pdf_path)
                        print(f"[OK] Downloaded: {pdf_path}")
                    except Exception as e:
                        print(f"[ERROR] Download failed: {e}")
                        sys.exit(1)
            search_and_download(args.paper or args.paper_id, max_results=5)
        elif args.pdf:
            output_dir = ensure_dirs(os.path.basename(args.pdf)[:30])
            extract_paper(args.pdf, output_dir)
        else:
            output_dir = ensure_dirs("default")
            symbols = [s.strip() for s in args.symbols.split(",")]
            reproduce(symbols, args.strategy, args.start, args.end, args.target_vol, output_dir)
    else:
        full_pipeline(args)


if __name__ == "__main__":
    main()

