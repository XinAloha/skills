# skill-factor-alpha191-alpha101

[简体中文](README.md) | **English**

> Alpha101 + Alpha191 factor library based on JoinQuant formulas: compute daily factor values from long-form OHLCV CSV data and export wide factor CSV files.

<p align="center">
  <img alt="libraries" src="https://img.shields.io/badge/libraries-Alpha101%20%2B%20Alpha191-blue">
  <img alt="factors" src="https://img.shields.io/badge/factors-292-brightgreen">
  <img alt="type" src="https://img.shields.io/badge/type-factor--library-blue">
  <img alt="platform" src="https://img.shields.io/badge/platform-Codex-9cf">
  <img alt="status" src="https://img.shields.io/badge/status-stable-brightgreen">
  <img alt="validation" src="https://img.shields.io/badge/validation-L3%20verified-success">
  <img alt="license" src="https://img.shields.io/badge/license-GPLv3-blue">
</p>

`skill-factor-alpha191-alpha101` is a classic formula factor-library skill for computing Alpha101 and Alpha191 factor values based on JoinQuant formulas.

This repository is suitable for:

- Batch generation of classic Alpha101 / Alpha191 formula factors
- Building factor matrices from daily long-form OHLCV data, including A-share data
- Preparing data for downstream factor evaluation, factor selection, model training, or backtesting
- Triggering deterministic factor computation workflows from Codex conversations

This repository only computes factor values. It does not call LLMs, read API keys, compute IC/ICIR, run backtests, or provide trading recommendations.

## Repository Contents

This repository contains two formula factor libraries:

| Library | Range | Output file | Description |
|---|---:|---|---|
| Alpha101 | `alpha_001` to `alpha_101` | `alpha101_values.csv` | Formulas based on JoinQuant Alpha101 |
| Alpha191 | `alpha_001` to `alpha_191` | `alpha191_values.csv` | Formulas based on JoinQuant Alpha191 |

The implementation was migrated from the local `compute_alpha101_skill.py` and `compute_alpha191_skill.py` workflows into a self-contained structure that can be called from the CLI or Codex. Both Alpha101 and Alpha191 are implemented based on JoinQuant formulas and corrected using comparisons with factor values from the JoinQuant API.

Some formulas require industry data, market capitalization, benchmark index data, or other inputs. When the required data is unavailable, the related factors do not stop the whole run; they are recorded in `skipped_factors.json`.

## Repository Structure

```text
skill-factor-alpha191-alpha101/
├── SKILL.md
├── README.md
├── README.en.md
├── agents/
│   └── openai.yaml
├── examples/
│   ├── compute_input.json
│   └── toy_market_data.csv
├── references/
│   ├── input_schema.md
│   ├── output_contract.md
│   ├── source_boundary.md
│   └── validation_notes.md
└── scripts/
    ├── compute_alpha_factors.py
    └── alpha_runtime/
        ├── alpha101_formulas.py
        ├── alpha191_formulas.py
        ├── alpha_compute.py
        ├── data.py
        ├── runtime.py
        └── selector.py
```

## Data Requirements

The first version supports only long-form CSV input. Each row is one stock on one trading day.

Required columns:

```text
date, symbol, open, high, low, close, volume
```

Optional columns:

```text
amount, vwap, adjfactor, pre_close, limit_up, limit_down
```

Runtime rules:

| Field / rule | Description |
|---|---|
| `date` | Accepts `YYYYMMDD` or `YYYY-MM-DD`; normalized to `YYYYMMDD` at runtime |
| `symbol` | Treated as a string |
| Missing `vwap` | Derived as `amount / volume` when both fields are available |
| Missing `amount` | Approximated as `close * volume` |
| Existing `adjfactor` | Price fields are converted to unadjusted prices before factor computation |
| `benchmark_csv_path` | Optional; used by Alpha191 formulas that require benchmark index data |

## Quick Start

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the example config:

```bash
python scripts/compute_alpha_factors.py --input examples/compute_input.json
```

Override the output directory:

```bash
python scripts/compute_alpha_factors.py --input examples/compute_input.json --output outputs/my_alpha_run
```

`--output` overrides `output_dir` in the input JSON.

## Input Config

See [examples/compute_input.json](examples/compute_input.json).

```json
{
  "market_data_csv_path": "toy_market_data.csv",
  "output_dir": "outputs/alpha_compute_example",
  "alpha_sets": ["alpha101", "alpha191"],
  "alpha_names": [
    "alpha101:alpha_001",
    "alpha101:alpha_002",
    "alpha191:alpha_001",
    "alpha191:alpha_018"
  ],
  "exclude_alpha_names": [],
  "start_date": "",
  "end_date": "",
  "symbols": [],
  "output_format": "csv",
  "output_layout": "wide",
  "n_jobs": 1,
  "show_progress": true
}
```

Core fields:

| Field | Type | Description |
|---|---|---|
| `market_data_csv_path` | string | Long-form market data CSV path. Relative paths are resolved from the input JSON directory, then the skill root, then `examples/` |
| `benchmark_csv_path` | string | Optional benchmark index CSV. It must include `date` and at least one of `close` or `open` |
| `output_dir` | string | Output directory. Relative paths in JSON are resolved from the skill root |
| `alpha_sets` | list/string | `alpha101`, `alpha191`, or both. Empty means both libraries are computed |
| `alpha_names` | list/string | Empty means all factors from selected libraries. Supports `alpha_001`, `1`, and `alpha101:alpha_001` |
| `exclude_alpha_names` | list/string | Factors to remove after selection. Qualified names are supported |
| `start_date` / `end_date` | string | Optional inclusive date filters |
| `symbols` | list[string] | Optional stock universe filter. Empty means all symbols |
| `n_jobs` | integer | Worker count. Defaults to the machine logical CPU count when omitted |
| `show_progress` | bool | Whether to print progress bars |

`output_format` and `output_layout` are currently retained only as explanatory example fields. The actual code always writes wide CSV outputs; changing these fields does not change the output format.

## Factor Selection

Compute only Alpha101:

```json
{
  "alpha_sets": ["alpha101"],
  "alpha_names": []
}
```

Compute only Alpha191:

```json
{
  "alpha_sets": ["alpha191"],
  "alpha_names": []
}
```

Compute selected factors from both libraries:

```json
{
  "alpha_sets": ["alpha101", "alpha191"],
  "alpha_names": ["alpha101:alpha_001", "alpha191:alpha_018"]
}
```

Exclude selected factors:

```json
{
  "alpha_sets": ["alpha191"],
  "exclude_alpha_names": ["alpha_075", "alpha_181"]
}
```

## Output Files

The run writes outputs under `output_dir`:

```text
outputs/alpha_compute_example/
├── alpha101_values.csv
├── alpha191_values.csv
├── alpha_compute_summary.json
├── skipped_factors.json
└── run_config.json
```

| File | Description |
|---|---|
| `alpha101_values.csv` | Wide Alpha101 factor values. Generated only when at least one Alpha101 factor is computed successfully |
| `alpha191_values.csv` | Wide Alpha191 factor values. Generated only when at least one Alpha191 factor is computed successfully |
| `alpha_compute_summary.json` | Run summary, including input path, output paths, sample date range, factor counts, and skipped count |
| `skipped_factors.json` | Factors that returned `None` or failed computation |
| `run_config.json` | Copy of the input config used for the run |

Wide CSV layout:

```text
date,symbol,alpha_001,alpha_002,...
```

Each row is one `(date, symbol)` observation, and each factor is one column. Alpha101 and Alpha191 are exported to separate files instead of being mixed into one CSV.

## Large-Sample Recommendations

Full-market, long-date-range, full Alpha101/Alpha191 runs can produce very large wide CSV files. Recommended practice:

- Run Alpha101 and Alpha191 separately to reduce peak memory and IO pressure.
- Do not blindly set `n_jobs` to the maximum CPU count; higher parallelism increases memory, scheduling, and disk-write pressure.
- If the server is already running other compute jobs, start with `n_jobs: 8`, `16`, or `24`.
- Before production-scale validation, run a smoke test on a shorter date range and a small factor subset.

## Validation Scope

The current validation level is `L3 verified`. Here, verified means formula-library reproduction, real-data runtime completeness, and Codex runtime consistency verification. It does not mean predictive-performance or trading-performance verification.

Verified scope:

- Real A-share long-form OHLCV data runs successfully from `20230601` to `20251231`.
- Alpha101 requests 101 factors, computes 82; some factors that depend on external data sources have not been validated yet.
- Alpha191 requests 191 factors, computes 186; some factors that depend on external data sources have not been validated yet.
- Codex Skill outputs match development-directory outputs on row count, columns, `date` / `symbol` keys, and NaN positions.
- Selected-factor runs match the corresponding columns from full runs exactly.

Not claimed:

- No claim about IC, ICIR, or long-short return effectiveness.
- No claim about trading performance or investment usability.
- No standalone backtest results are provided.

## Project Status and Risk Boundaries

- **Project status**: Community Project, not officially reviewed, certified, or endorsed by QUANTSKILLS.
- **Data source**: This repository includes toy data only. Real market, benchmark, industry, market-cap, or other data is user-provided, and users are responsible for data licensing and compliance.
- **Formula source**: Alpha101 and Alpha191 are implemented based on JoinQuant formulas and corrected using comparisons with user-authorized JoinQuant factor-value API outputs.
- **Core assumptions**: Input is daily long-form OHLCV CSV. Field definitions, price-adjustment method, universe, trading calendar, and missing-value handling affect the computed factor values.
- **Known limitations**: Some factors require industry, market-cap, benchmark-index, or other external fields. When required inputs are unavailable, affected factors are recorded in `skipped_factors.json`.
- **Risk boundary**: Outputs are formula factor values only. They do not imply factor effectiveness, predictive power, trading signals, portfolio returns, or production readiness.
- **Use**: For quantitative research, education, and methodology reference only. Not investment advice, rebalance advice, or profit assurance.

## Boundaries

| Boundary | Description |
|---|---|
| Factor Library | Computes Alpha101/Alpha191 factor values only |
| No LLM dependency | Does not call models or read API keys |
| No factor evaluation | Does not compute IC, ICIR, Rank IC, group returns, or backtest returns |
| No trading advice | Does not provide investment advice, rebalance recommendations, or performance guarantees |
| Long-form CSV input | The first version does not support databases, parquet, live APIs, or minute-level input |
| Wide CSV output | Currently always writes wide CSV outputs |

## License

This repository is licensed under the GNU General Public License v3.0. See [LICENSE](LICENSE).
