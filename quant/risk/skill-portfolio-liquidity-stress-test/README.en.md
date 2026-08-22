# Portfolio Liquidity Stress Test

Runs deterministic portfolio liquidation-capacity and pro-rata redemption scenarios.

## Quick start

```bash
python scripts/stress_liquidity.py --demo
python scripts/stress_liquidity.py --input your_data.csv --redemption-value 1000000 --out report.json
```

## CLI parameters

| Argument | Requirement | Description |
| --- | --- | --- |
| `--demo` | Choose exactly one source | Use built-in rows; mutually exclusive with `--input` |
| `--input <csv>` | Choose exactly one source | Read a UTF-8 CSV |
| `--participation <float>` | Optional | Daily participation cap, default `0.1`; finite and in `(0,1]` |
| `--volume-shock <float>` | Optional | Stressed ADV multiplier, default `0.5`; finite and positive |
| `--horizon-days <int>` | Optional | Trading-day horizon, default `5`; a positive integer within the model's finite numeric range |
| `--eta <float>` | Optional | Square-root impact coefficient, default `0.5`; finite and non-negative |
| `--redemption-value <float>` | Optional | Finite non-negative cash target; defaults to total portfolio value |
| `--out <json>` | Optional | Write JSON to a file; otherwise print to standard output |

The CSV must contain a unique non-empty `symbol` plus finite `position_value`, `adv`, `spread_bps`, and `volatility`. `position_value` and `adv` must use the same currency-value unit; derivatives require multiplier normalization. Redemption sales are allocated pro rata by position value and capped by each symbol's stressed horizon capacity.

Use [`skill-pandadata-api`](https://github.com/quantskills/skill-pandadata-api) for market-volume inputs. Holdings, redemption targets, and true bid-ask spreads normally come from the user, custodian, broker, or venue.

## Validation and limits

See [validation/README.md](validation/README.md). Square-root impact is a scenario model, not a calibrated execution forecast or guarantee.

GPL-3.0-only.
