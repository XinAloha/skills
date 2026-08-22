# Data Sources Guide

This skill uses third-party market data sources directly.

## akshare

Default source for Chinese futures.

Install:

```bash
python -m pip install akshare
```

Daily K-lines:

```python
import akshare as ak

df = ak.futures_zh_daily_sina(symbol="rb0")  # Rebar continuous
df = ak.futures_zh_daily_sina(symbol="IF0")  # CSI 300 index futures continuous
df = ak.futures_zh_daily_sina(symbol="rb2401")  # Specific contract month
```

Common continuous symbols:

| akshare symbol | Meaning |
| --- | --- |
| `rb0` | Rebar continuous |
| `IF0` | CSI 300 index futures continuous |
| `IC0` | CSI 500 index futures continuous |
| `AU0` | Gold continuous |
| `CU0` | Copper continuous |
| `SC0` | Crude oil continuous |

Expected columns:

```python
["date", "open", "high", "low", "close", "volume"]
```

## yfinance

Use for international instruments when appropriate.

Install:

```bash
python -m pip install yfinance
```

Examples:

```python
import yfinance as yf

gold = yf.download("GC=F", start="2020-01-01")
oil = yf.download("CL=F", start="2020-01-01")
sp500 = yf.download("^GSPC", start="2020-01-01")
```

## CSV Data

Use CSV when the paper or user provides a custom dataset.

Required columns:

```csv
date,open,high,low,close,volume
2020-01-02,3580,3600,3560,3590,123456
2020-01-03,3590,3620,3570,3610,134567
```

Load:

```python
import pandas as pd

df = pd.read_csv("my_data.csv")
df["date"] = pd.to_datetime(df["date"])
df = df.sort_values("date").reset_index(drop=True)
```

## Data Quality Checks

Always record:

- source name and function/API used
- requested date range
- loaded date range
- latest available date
- missing values and duplicate dates

Useful checks:

```python
df["date"] = pd.to_datetime(df["date"])
print(df["date"].min(), df["date"].max())
print(df.isna().sum())
print(df.duplicated(subset=["date"]).sum())
```

Known caveat: free APIs can be delayed or stale. Always check the latest date
before trusting a result.
