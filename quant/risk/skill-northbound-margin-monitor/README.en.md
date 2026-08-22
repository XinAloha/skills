# skill-northbound-margin-monitor

A-share Northbound Capital + Margin Trading + Stock Index Futures Panorama Monitoring System. Daily automated collection of Shanghai-Hong Kong Stock Connect capital flows, margin trading data, and stock index futures data. Through **25 signal detectors** and **4 resonance/divergence patterns**, combined with **LLM macro analysis** (DeepSeek/Claude), it generates a comprehensive sentiment scoring daily report (12-section Markdown + JSON).

## Features

- **Five-Dimensional Signal System**: Northbound (7) + Margin (7) + Futures (3) + Price/Volume (2) + Microstructure (7) = 25 detectors
- **Dual-Source Resilience**: Pandadata (margin individual stocks) + AKShare (northbound/futures/limit-up-down), multi-level auto-degradation
- **LLM Macro Analysis**: DeepSeek/Claude API (with exponential backoff retry + timeout) + rule-engine fallback
- **Resonance/Divergence Detection**: 4 cross-asset signal pattern recognitions
- **Signal Decay**: Half-life exponential decay to prevent persistent signal inflation
- **Data Source Transparency**: 10 standardized labels, each signal annotated with its real data source
- **Composite Scoring**: Five-dimensional weighted 0-100 score + risk penalty + ★1-5 risk rating
- **Industry-Neutral Ranking**: Z-score eliminates industry-scale bias in margin exposure ranking
- **Historical Comparison**: Item-by-item comparison with the previous trading day
- **Dual-Format Output**: Markdown 12-section daily + JSON structured data
- **Date-Based Caching**: Same-day data auto-reuse + Shenwan offline backup (never expires)
- **540 Tests**: 101 test classes covering all modules

## Installation

```bash
# Clone the repository
git clone <repo-url>
cd skill-northbound-margin-monitor

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env and fill in Pandadata credentials:
#   DEFAULT_USERNAME=86xxxxxxxxxxx
#   DEFAULT_PASSWORD=your_password

# LLM API Key (optional; rule-engine fallback used when absent)
#   ANTHROPIC_API_KEY=sk-xxx           # Claude
#   ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropic  # DeepSeek
```

### Dependencies

- Python >= 3.10
- panda_data >= 0.0.9 (margin trading data)
- akshare >= 1.18.0 (northbound/futures/limit data)
- anthropic >= 0.39.0 (LLM API)
- tenacity >= 8.0 (LLM retry)
- pandas >= 2.0.0, numpy >= 1.22, < 2.0
- streamlit >= 1.28.0 (dashboard)

## Usage

```bash
# Default run (latest trading day, use cache)
python run.py

# Specify a date
python run.py --date 20260630

# Force fetch latest data (skip cache)
python run.py --date 20260630 --no-cache

# Summary mode (LLM 150-200 char summary)
python run.py --summary

# Customize TOP-N count + verbose logging
python run.py --top-n 30 --verbose

# Cleanup cache (delete data older than 30 days)
python run.py --cleanup-cache 30
```

## Output

```
output/
  2026-07-02/
    panorama_monitor_20260702.md   # Markdown daily (12 sections)
    panorama_monitor_20260702.json # JSON structured data

cache/
  YYYYMMDD/                        # Daily cache
  nb_flow_history.parquet          # Northbound flow cumulative history
  sw_industry_mapping.parquet      # Shenwan industry classification cache (30-day)
  shenwan_backup.parquet           # Shenwan offline backup (never expires)
```

### Daily Report Sections

1. **Northbound Capital Overview** — 7 signals + data source labels + summary
2. **Margin Trading Overview** — 7 signals + macro data + individual stock TOP10
3. **Stock Index Futures Signals** — 3 signals (basis/OI/resonance) + index summaries
4. **Resonance/Divergence Analysis** — 4 cross-asset patterns
5. **Price/Volume Confirmation** — Index momentum + volatility regime
6. **Microstructure Signals** — Breadth/volume/turnover/limit-up-down/main fund/dragon-tiger-board/new-high-low
7. **Composite Sentiment Assessment** — 5-dimension sub-scores + total + risk penalty
8. **Historical Comparison** — Item-by-item comparison with previous trading day
9. **AI Macro Analysis** — LLM or rule-engine comprehensive analysis
10. **Sector Capital Flow** — Industry margin exposure Z-score ranking
11. **Comprehensive Risk Assessment** — 4-factor decomposition + risk signal checklist
12. **Data Provenance** — Source + status for each data category (✅/⚠️)

## Project Structure

```
skill-northbound-margin-monitor/
├── SKILL.md                         # Agent workflow entry point
├── README.md                        # Project introduction (Chinese)
├── README.en.md                     # Project introduction (English)
├── OPERATION_MANUAL.md              # Detailed operation manual
├── LICENSE                          # GPLv3
├── config.json                      # Runtime config (weights + thresholds + LLM params)
├── pyproject.toml                   # Python project metadata
├── .env.example                     # Environment variable template
├── requirements.txt                 # Python dependencies
├── run.py                           # CLI entry point
├── mcp_server.py                    # MCP server (3 tools)
├── core/
│   ├── data_fetcher.py              # Dual-source data acquisition (Pandadata + AKShare + HKEX)
│   ├── flow_accumulator.py          # Northbound flow daily history accumulator
│   ├── northbound.py                # Northbound 7 signals (registry pattern)
│   ├── margin.py                    # Margin 7 signals (registry pattern)
│   ├── futures.py                   # Futures 3 signals (registry pattern)
│   ├── price_volume.py              # Price/Volume 2 confirmation signals
│   ├── microstructure.py            # Microstructure 7 signals
│   ├── resonance.py                 # 4 cross-asset resonance/divergence patterns
│   ├── scorer.py                    # Five-dimensional weighted scoring + risk rating
│   ├── reporter.py                  # Markdown + JSON dual output
│   ├── pipeline.py                  # End-to-end pipeline
│   ├── cache.py                     # Date-partitioned Parquet cache
│   └── backtest.py                  # Backtest framework (IC + stratification + regime decomposition)
├── llm/
│   └── analyst.py                   # LLM macro analysis (exponential backoff + rule fallback)
├── dashboard/
│   └── app.py                       # Streamlit dashboard
├── tests/                           # 540 tests (101 test classes)
├── references/
│   ├── data-sources.md              # Data source documentation with fallback paths
│   ├── report-template.md           # 12-section daily template + LLM prompt
│   └── advanced-features.md         # Streamlit / MCP / Backtest / Cache management
├── scripts/
│   └── validate_report.py           # Report integrity validator
├── agents/
│   ├── openai.yaml                  # OpenAI/Codex adapter
│   ├── cursor-rule.mdc              # Cursor IDE adapter
│   └── portable-loader.md           # Generic loader for any agent
├── cache/                           # Data cache
└── output/                          # Report output
    └── YYYY-MM-DD/
        ├── panorama_monitor_YYYYMMDD.md
        └── panorama_monitor_YYYYMMDD.json
```

## Testing

```bash
# Run all 540 tests
python -m pytest tests/ -q

# By module
python -m pytest tests/test_northbound.py -q
python -m pytest tests/test_margin.py -q

# With coverage
python -m pytest tests/ --cov=core --cov-report=term-missing
```

## Configuration

`config.json` allows adjustment of all thresholds and weights:

| Config Item | Default | Description |
|---|---|---|
| `northbound.consecutive_days_threshold` | 3 | Consecutive inflow/outflow day threshold |
| `northbound.anomaly_zscore_threshold` | 2.0 | Single-day anomaly Z-score threshold |
| `margin.buy_ratio_hot` | 0.10 | Margin buy ratio active line |
| `margin.buy_ratio_dangerous` | 0.15 | Margin buy ratio danger line |
| `margin.extreme_percentile` | 95 | Extreme overheat percentile |
| `margin.ice_point_percentile` | 5 | Extreme freeze percentile |
| `futures.basis_threshold` | 0.3 | Basis direction threshold |
| `futures.oi_change_threshold` | 2.0 | Open interest change threshold |
| `scoring.northbound_weight` | 0.18 | Northbound weight (recalibrated from 0.35, 2026-07) |
| `scoring.margin_weight` | 0.38 | Margin weight |
| `scoring.futures_weight` | 0.20 | Futures weight |
| `scoring.pv_weight` | 0.08 | Price/Volume weight |
| `scoring.micro_weight` | 0.16 | Microstructure weight (recalibrated from 0.05, 2026-07) |
| `llm.timeout` | 120.0 | LLM API timeout (seconds) |
| `llm.max_retries` | 2 | HTTP-level retries |
| `llm.llm_retries` | 3 | Exponential backoff LLM retries |

## Data Sources

| Data | Primary Source | Fallback | Degradation Strategy |
|---|---|---|---|
| Margin individual stocks | Pandadata `get_margin()` | AKShare SSE/SZSE | Auto-switch |
| Margin macro | AKShare `macro_china_market_margin_sh/sz` | — | — |
| Northbound summary | AKShare `stock_hsgt_hist_em` | CSI300 proxy | 4-level degradation chain |
| Northbound flow | AKShare `stock_hsgt_fund_flow_summary_em` | — | Advance/decline ratio substitution |
| Northbound flow history | FlowAccumulator accumulation | Real-time rebuild | — |
| Stock index futures | AKShare `futures_main_sina` + `stock_zh_index_daily` | — | — |
| Stock info | Pandadata `get_stock_detail` | — | — |
| Shenwan industry | AKShare `stock_board_industry_name_em` | 30-day cache → offline backup | Never-expiring backup |
| HKEX supplement | HKEX CSV | — | best-effort |
| Limit-up/down | AKShare `stock_zt_pool_em` | — | best-effort |
| LLM analysis | DeepSeek / Claude API | Rule-engine fallback | Auto-degradation |

**Known Data Limitations**: Northbound `net_buy_amount` has been NaN since 2024-08 and was permanently cancelled as of July 2026. `market_value` has been all zeros since 2026-04. The system automatically uses FlowAccumulator + CSI300 index as a proxy. Each signal's report table is annotated with its real data source.

## License

GPLv3
