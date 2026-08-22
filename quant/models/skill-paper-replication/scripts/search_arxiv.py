#!/usr/bin/env python3
"""
arxiv Paper Search — 搜索量化金融论文

用法:
    python search_arxiv.py "momentum futures portfolio" [--max 10] [--sort date] [--download] [--output-dir ./output]

支持 arxiv API 查询语法:
    python search_arxiv.py "all:momentum AND all:futures" --max 5
    python search_arxiv.py "ti:quantitative trading" --sort submittedDate --descending
"""

import argparse
import json
import os
import sys
import time
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET


ARXIV_API = "http://export.arxiv.org/api/query"
CATEGORIES = {
    "qfin": "Quantitative Finance",
    "qfin.CP": "Computational Finance",
    "qfin.EC": "Economics",
    "qfin.GN": "General Finance",
    "qfin.MF": "Mathematical Finance",
    "qfin.PM": "Portfolio Management",
    "qfin.PR": "Pricing of Securities",
    "qfin.RM": "Risk Management",
    "qfin.ST": "Statistical Finance",
    "qfin.TR": "Trading and Market Microstructure",
}


def search_arxiv(query, max_results=10, sort_by="relevance", descending=False, start=0):
    """Search arxiv using the API and return parsed results."""
    params = {
        "search_query": query,
        "start": start,
        "max_results": max_results,
        "sortBy": sort_by,
        "sortOrder": "descending" if descending else "ascending",
    }
    url = f"{ARXIV_API}?{urllib.parse.urlencode(params)}"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "PaperReplicationAgent/1.0"})
        with urllib.request.urlopen(req, timeout=30) as response:
            xml_data = response.read().decode("utf-8")
    except Exception as e:
        print(f"[ERROR] arxiv API request failed: {e}")
        return []

    # Parse XML
    ns = {
        "atom": "http://www.w3.org/2005/Atom",
        "arxiv": "http://arxiv.org/schemas/atom",
    }
    root = ET.fromstring(xml_data)

    # Check for API errors
    error_elem = root.find("atom:link[@rel='self']", ns)
    if error_elem is None and len(root.findall("atom:entry", ns)) == 0:
        # Check opensearch:totalResults
        total = root.find("opensearch:totalResults", {"opensearch": "http://a9.com/-/spec/opensearch/1.1/"})
        if total is not None and total.text == "0":
            print("[INFO] No results found.")
            return []

    results = []
    for entry in root.findall("atom:entry", ns):
        paper = {}
        paper["id"] = entry.find("atom:id", ns).text.split("/abs/")[-1]
        paper["title"] = entry.find("atom:title", ns).text.strip().replace("\n", " ")
        paper["summary"] = entry.find("atom:summary", ns).text.strip().replace("\n", " ")[:300]
        paper["published"] = entry.find("atom:published", ns).text[:10]
        paper["updated"] = entry.find("atom:updated", ns).text[:10]

        # Authors
        authors = [a.find("atom:name", ns).text for a in entry.findall("atom:author", ns)]
        paper["authors"] = ", ".join(authors[:3])
        if len(authors) > 3:
            paper["authors"] += f" et al. ({len(authors)} authors)"

        # Categories
        cats = [c.get("term") for c in entry.findall("atom:category", ns)]
        paper["categories"] = cats

        # PDF link
        pdf_link = ""
        for link in entry.findall("atom:link", ns):
            if link.get("title") == "pdf":
                pdf_link = link.get("href")
        paper["pdf_url"] = pdf_link
        paper["abs_url"] = f"https://arxiv.org/abs/{paper['id']}"

        results.append(paper)

    return results


def download_pdf(paper_id, output_dir="./output"):
    """Download PDF for a given arxiv paper ID."""
    os.makedirs(output_dir, exist_ok=True)
    pdf_url = f"https://arxiv.org/pdf/{paper_id}.pdf"
    filename = os.path.join(output_dir, f"{paper_id.replace('/', '_')}.pdf")

    if os.path.exists(filename):
        print(f"  [SKIP] Already exists: {filename}")
        return filename

    try:
        req = urllib.request.Request(pdf_url, headers={"User-Agent": "PaperReplicationAgent/1.0"})
        with urllib.request.urlopen(req, timeout=60) as response:
            with open(filename, "wb") as f:
                f.write(response.read())
        print(f"  [OK] Downloaded: {filename}")
        return filename
    except Exception as e:
        print(f"  [ERROR] Download failed: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(description="Search arxiv for quantitative finance papers")
    parser.add_argument("query", help="Search query (e.g., 'momentum futures portfolio')")
    parser.add_argument("--max", type=int, default=10, help="Max results (default: 10)")
    parser.add_argument("--sort", choices=["relevance", "lastUpdatedDate", "submittedDate"], default="relevance")
    parser.add_argument("--desc", action="store_true", help="Sort descending")
    parser.add_argument("--download", action="store_true", help="Download PDFs of results")
    parser.add_argument("--output-dir", default="./output", help="Output directory for PDFs")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    print(f"[*] Searching arxiv: '{args.query}'")
    print(f"[*] Sort: {args.sort} {'(descending)' if args.desc else ''}")
    print(f"[*] Max results: {args.max}")
    print()

    # Rate limiting — be nice to arxiv API
    time.sleep(0.5)

    results = search_arxiv(args.query, max_results=args.max, sort_by=args.sort, descending=args.desc)

    if not results:
        print("[!] No results found.")
        return

    if args.json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
        return

    print(f"[+] Found {len(results)} papers:\n")
    print("=" * 80)

    for i, paper in enumerate(results, 1):
        print(f"\n[{i}] {paper['title']}")
        print(f"    ID:     {paper['id']}")
        print(f"    Authors: {paper['authors']}")
        print(f"    Date:   {paper['published']} (updated {paper['updated']})")
        print(f"    Cats:   {', '.join(paper['categories'])}")
        print(f"    Summary: {paper['summary']}...")
        print(f"    URL:    {paper['abs_url']}")

        if args.download and paper["pdf_url"]:
            download_pdf(paper["id"], args.output_dir)

    print("\n" + "=" * 80)
    print(f"[*] Done. {len(results)} papers displayed.")

    if args.download:
        print(f"[*] PDFs saved to: {os.path.abspath(args.output_dir)}")


if __name__ == "__main__":
    main()
