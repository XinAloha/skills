#!/usr/bin/env python3
"""
Paper PDF Extractor — 从 PDF 中提取论文关键信息

用法:
    python extract_paper.py --pdf paper.pdf [--markdown] [--formulas] [--tables] [--full]

提取内容:
  - 标题、摘要、作者、日期
  - 核心公式（检测包含数学符号的段落）
  - 表格数据
  - 回测指标（Sharpe, MaxDD, 年化收益等）
  - 资产池和回测参数
"""

import argparse
import json
import os
import re
import sys


def extract_metadata(doc):
    """Extract paper metadata."""
    meta = {}
    meta["title"] = ""
    meta["authors"] = ""
    meta["abstract"] = ""

    # Try to get from document metadata
    meta["title"] = doc.metadata.get("title", "")
    meta["author"] = doc.metadata.get("author", "")

    return meta


def detect_title(text):
    """Detect paper title from first page text."""
    # Title is usually the first few lines, before abstract/introduction
    lines = text.strip().split("\n")
    title_lines = []
    for line in lines[:20]:
        line = line.strip()
        if not line:
            continue
        if len(line) < 100 and not line.startswith(("Abstract", "Introduction", "Keywords", "I.", "1.")):
            title_lines.append(line)
        elif title_lines:
            break
    return " ".join(title_lines) if title_lines else ""


def extract_abstract(text):
    """Extract abstract text."""
    patterns = [
        r"(?:Abstract|摘要)\s*[:：]?\s*\n?(.*?)(?:\n\s*\n|\n(?:Keywords|Index|Introduction|1\.|I\.))",
        r"(?:Abstract|摘要)\s*[:：]?\s*(.*?)(?:Keywords|Index|Introduction|1\.|I\.)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return ""


def find_formulas(text):
    """Find lines that likely contain formulas (mathematical expressions)."""
    # Simple string matching (no regex) for formula detection
    formula_keywords = [
        '\\\\',          # LaTeX backslash commands
        'alpha', 'beta', 'gamma', 'delta', 'epsilon', 'theta', 'lambda',
        'sigma', 'mu', 'omega', 'pi', 'rho', 'tau', 'phi', 'psi',
        'frac{', 'sum', 'prod', 'int{', 'partial', 'nabla',
        'w_i', 'w_j', 'sigma_', 'Sigma',
        'variance', 'covariance', 'volatility',
    ]
    formulas = []
    for line in text.split("\n"):
        line = line.strip()
        if len(line) < 10 or len(line) > 200:
            continue
        for keyword in formula_keywords:
            if keyword in line:
                formulas.append(line)
                break
    return formulas


def find_tables(text):
    """Find table-like structures in text."""
    tables = []
    # Look for lines that look like table headers
    table_pattern = re.compile(r'(?:Table|TABLE|表)\s*\d+', re.IGNORECASE)
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if table_pattern.search(line):
            # Capture the table caption and nearby lines
            table_text = line.strip()
            for j in range(i + 1, min(i + 20, len(lines))):
                if lines[j].strip() and len(lines[j].strip()) < 150:
                    table_text += "\n" + lines[j].strip()
                else:
                    break
            tables.append(table_text)
    return tables


def extract_metrics(text):
    """Extract quantitative metrics from text."""
    metrics = {}

    # Sharpe ratio
    sharpe_patterns = [
        r'(?:Sharpe|夏普)[\s比率ratio:：]*([+-]?\d+\.?\d*)',
    ]
    for p in sharpe_patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            metrics["sharpe"] = float(m.group(1))
            break

    # Max drawdown
    mdd_patterns = [
        r'(?:Max\s*Drawdown|最大回撤)[\s:：]*([+-]?\d+\.?\d*)\s*%',
        r'(?:Max\s*Drawdown|最大回撤)[\s:：]*([+-]?\d+\.?\d*)',
    ]
    for p in mdd_patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            metrics["max_drawdown"] = float(m.group(1))
            break

    # Annualized return
    ann_patterns = [
        r'(?:Annual(?:ized)?\s*Return|年化(?:收益|回报|收益率))[\s:：]*([+-]?\d+\.?\d*)\s*%',
    ]
    for p in ann_patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            metrics["annual_return"] = float(m.group(1))
            break

    # Volatility
    vol_patterns = [
        r'(?:Volatility|波动率)[\s:：]*([+-]?\d+\.?\d*)\s*%',
    ]
    for p in vol_patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            metrics["volatility"] = float(m.group(1))
            break

    return metrics


def find_asset_universe(text):
    """Try to identify the asset universe mentioned."""
    # Common Chinese futures symbols
    futures = ["rb", "HC", "IF", "IC", "IH", "AU", "AG", "CU", "AL", "ZN",
               "NI", "SN", "PB", "SC", "FU", "MA", "TA", "PP", "SA",
               "AP", "CF", "SR", "OI", "P", "M", "Y", "RM", "SM", "SF", "JM",
               "J", "I", "EG", "L", "V"]
    found = []
    for f in futures:
        if f.upper() in text.upper():
            found.append(f)
    return list(set(found))[:20]


def extract_pdf(pdf_path, output_markdown=False, output_formulas=False,
                output_tables=False, output_full=False):
    """Main extraction function."""
    import fitz

    doc = fitz.open(pdf_path)
    full_text = ""
    page_texts = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text()
        page_texts.append(text)
        full_text += f"\n--- PAGE {page_num + 1} ---\n{text}"

    doc.close()

    result = {
        "file": pdf_path,
        "pages": len(page_texts),
        "metadata": extract_metadata(doc),
        "title": detect_title(page_texts[0]) if page_texts else "",
        "abstract": extract_abstract(full_text),
        "formulas": find_formulas(full_text),
        "tables": find_tables(full_text),
        "metrics": extract_metrics(full_text),
        "assets": find_asset_universe(full_text),
    }

    return result, full_text


def format_markdown(result, full_text=None):
    """Format extraction result as markdown."""
    lines = []
    lines.append(f"# {result['title']}")
    lines.append("")
    lines.append(f"**PDF**: {result['file']} | **Pages**: {result['pages']}")
    lines.append("")

    if result["abstract"]:
        lines.append("## Abstract")
        lines.append(result["abstract"][:500])
        lines.append("")

    if result["formulas"]:
        lines.append("## Detected Formulas")
        for i, f in enumerate(result["formulas"], 1):
            lines.append(f"{i}. `{f}`")
        lines.append("")

    if result["tables"]:
        lines.append("## Detected Tables")
        for i, t in enumerate(result["tables"], 1):
            lines.append(f"### Table {i}")
            lines.append(t)
            lines.append("")

    if result["metrics"]:
        lines.append("## Extracted Metrics")
        for k, v in result["metrics"].items():
            lines.append(f"- **{k}**: {v}")
        lines.append("")

    if result["assets"]:
        lines.append(f"## Mentioned Assets ({len(result['assets'])})")
        lines.append(", ".join(result["assets"]))
        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Extract key information from research paper PDFs")
    parser.add_argument("--pdf", required=True, help="Path to PDF file")
    parser.add_argument("--markdown", action="store_true", help="Output as markdown")
    parser.add_argument("--formulas", action="store_true", help="Show detected formulas only")
    parser.add_argument("--tables", action="store_true", help="Show detected tables only")
    parser.add_argument("--metrics", action="store_true", help="Show extracted metrics only")
    parser.add_argument("--full", action="store_true", help="Output full text")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--output", help="Output file path")
    args = parser.parse_args()

    if not os.path.exists(args.pdf):
        print(f"[ERROR] File not found: {args.pdf}")
        sys.exit(1)

    print(f"[*] Extracting from: {args.pdf}")
    result, full_text = extract_pdf(args.pdf)

    # Determine output format
    if args.json:
        output = json.dumps(result, indent=2, ensure_ascii=False)
    elif args.formulas:
        output = "\n".join(result["formulas"])
    elif args.tables:
        output = "\n\n".join(result["tables"])
    elif args.metrics:
        output = json.dumps(result["metrics"], indent=2)
    elif args.full:
        output = full_text
    elif args.markdown:
        output = format_markdown(result, full_text)
    else:
        output = format_markdown(result, full_text)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"[*] Saved to: {args.output}")
    else:
        print()
        print(output)

    # Summary
    print(f"\n[*] Extraction complete:")
    print(f"    Pages: {result['pages']}")
    print(f"    Formulas found: {len(result['formulas'])}")
    print(f"    Tables found: {len(result['tables'])}")
    print(f"    Metrics found: {len(result['metrics'])}")
    print(f"    Assets mentioned: {', '.join(result['assets']) if result['assets'] else 'none'}")


if __name__ == "__main__":
    main()
