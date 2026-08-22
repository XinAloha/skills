from __future__ import annotations

import argparse
import hashlib
import json
import os
import shlex
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Sequence

import numpy as np
import pandas as pd


SIGNAL_COLUMN = "prediction"
BACKTEST_SKILL_DIRNAME = "skill-factor-backtest"
BACKTEST_ENTRYPOINT = Path("scripts") / "run_factor_backtest.py"


@dataclass(frozen=True)
class BacktestSignalExport:
    signal_path: Path
    manifest_path: Path
    start_date: int
    end_date: int
    row_count: int
    symbol_count: int


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_table(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix in {".parquet", ".pq"}:
        return pd.read_parquet(path)
    if suffix == ".csv":
        return pd.read_csv(path)
    raise ValueError(f"Unsupported table format: {path}. Use CSV or Parquet.")


def _prediction_columns(frame: pd.DataFrame) -> pd.DataFrame:
    if {"datetime", "symbol"}.issubset(frame.columns):
        flat = frame
    else:
        flat = frame.reset_index()
    required = {"datetime", "symbol", SIGNAL_COLUMN}
    missing = sorted(required.difference(flat.columns))
    if missing:
        raise ValueError(
            "OOS predictions must contain datetime, symbol, and prediction; "
            f"missing: {', '.join(missing)}"
        )
    return flat.loc[:, ["datetime", "symbol", SIGNAL_COLUMN]].copy()

def _normalize_dates(values: pd.Series) -> pd.Series:
    raw = values.astype("string").str.strip()
    integer_dates = raw.str.fullmatch(r"\d{8}").fillna(False)
    dates = pd.Series(pd.NaT, index=values.index, dtype="datetime64[ns]")
    if integer_dates.any():
        dates.loc[integer_dates] = pd.to_datetime(raw[integer_dates], format="%Y%m%d", errors="coerce")
    if (~integer_dates).any():
        dates.loc[~integer_dates] = pd.to_datetime(raw[~integer_dates], errors="coerce")
    if dates.isna().any():
        raise ValueError("OOS predictions contain invalid datetime values")
    return dates


def _normalize_integer_tickers(values: pd.Series, source_name: str) -> pd.Series:
    raw = values.astype("string").str.strip()
    invalid_format = raw.isna() | ~raw.str.fullmatch(r"[+-]?\d+")
    if invalid_format.any():
        examples = sorted(raw[invalid_format].dropna().unique().tolist())[:5]
        raise ValueError(
            f"{source_name} contains non-integer security codes: {examples}. "
            "Provide --ticker-map with symbol and ticker columns."
        )
    numeric = pd.to_numeric(raw, errors="coerce")
    invalid_numeric = numeric.isna() | ~np.isfinite(numeric) | (numeric < 0)
    if invalid_numeric.any():
        raise ValueError(f"{source_name} contains invalid integer security codes")
    return numeric.astype("int64")


def _map_tickers(symbols: pd.Series, ticker_map_path: Path | None) -> tuple[pd.Series, dict]:
    if ticker_map_path is None:
        return _normalize_integer_tickers(symbols, "symbol"), {"mode": "direct_integer"}

    mapping_path = ticker_map_path.resolve()
    if not mapping_path.is_file():
        raise FileNotFoundError(f"Ticker map does not exist: {mapping_path}")
    mapping = _read_table(mapping_path)
    missing = sorted({"symbol", "ticker"}.difference(mapping.columns))
    if missing:
        raise ValueError(f"Ticker map is missing columns: {', '.join(missing)}")
    mapping = mapping.loc[:, ["symbol", "ticker"]].copy()
    mapping["symbol_key"] = mapping["symbol"].astype("string").str.strip()
    if mapping["symbol_key"].isna().any() or mapping["symbol_key"].duplicated().any():
        raise ValueError("Ticker map symbols must be non-missing and unique")
    mapping["ticker"] = _normalize_integer_tickers(mapping["ticker"], "ticker map")
    if mapping["ticker"].duplicated().any():
        raise ValueError("Ticker map must map each symbol to a unique integer ticker")

    symbol_keys = symbols.astype("string").str.strip()
    lookup = mapping.set_index("symbol_key")["ticker"]
    tickers = symbol_keys.map(lookup)
    if tickers.isna().any():
        examples = sorted(symbol_keys[tickers.isna()].dropna().unique().tolist())[:5]
        raise ValueError(f"Ticker map does not cover OOS symbols: {examples}")
    return tickers.astype("int64"), {
        "mode": "mapping_file",
        "path": str(mapping_path),
        "sha256": _sha256(mapping_path),
    }


def export_backtest_signal(
    run_dir: str | Path,
    output_path: str | Path | None = None,
    ticker_map_path: str | Path | None = None,
    force: bool = False,
) -> BacktestSignalExport:
    run_path = Path(run_dir).resolve()
    required_artifacts = [
        run_path / "summary.json",
        run_path / "config.json",
        run_path / "oos_evaluation.json",
        run_path / "oos_predictions.parquet",
    ]
    missing = [path.name for path in required_artifacts if not path.is_file()]
    if missing:
        raise FileNotFoundError(
            "The run is not a completed frozen OOS evaluation; missing: " + ", ".join(missing)
        )

    source_path = run_path / "oos_predictions.parquet"
    destination = (
        Path(output_path).resolve()
        if output_path is not None
        else run_path / "backtest_input" / "prediction.parquet"
    )
    if destination.suffix.lower() not in {".parquet", ".pq"}:
        raise ValueError("Backtest signal output must use a Parquet suffix")
    manifest_path = destination.with_suffix(".manifest.json")

    frame = _prediction_columns(pd.read_parquet(source_path))
    dates = _normalize_dates(frame["datetime"])
    signal = pd.to_numeric(frame[SIGNAL_COLUMN], errors="coerce")
    invalid_signal = signal.isna() | ~np.isfinite(signal)
    if invalid_signal.any():
        raise ValueError(
            f"OOS predictions contain {int(invalid_signal.sum())} non-finite prediction values"
        )

    mapping_path = Path(ticker_map_path) if ticker_map_path is not None else None
    tickers, mapping_metadata = _map_tickers(frame["symbol"], mapping_path)
    exported = pd.DataFrame(
        {
            "date": dates.dt.strftime("%Y%m%d").astype("int64"),
            "ticker": tickers,
            SIGNAL_COLUMN: signal.astype("float64"),
        }
    )
    duplicate_mask = exported.duplicated(["date", "ticker"], keep=False)
    if duplicate_mask.any():
        examples = exported.loc[duplicate_mask, ["date", "ticker"]].head(5).to_dict("records")
        raise ValueError(f"Duplicate (date, ticker) rows after ticker conversion: {examples}")
    if exported.empty:
        raise ValueError("OOS predictions contain no rows")
    exported = exported.sort_values(["date", "ticker"], kind="stable").reset_index(drop=True)
    start_date = int(exported["date"].min())
    end_date = int(exported["date"].max())
    source_sha256 = _sha256(source_path)
    if not force and (destination.exists() or manifest_path.exists()):
        if not destination.is_file() or not manifest_path.is_file():
            raise FileExistsError(
                "Backtest signal output and manifest must either both exist or both be absent"
            )
        try:
            existing = pd.read_parquet(destination)
            existing_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise FileExistsError("Existing backtest signal artifacts are not readable") from exc
        if (
            existing.equals(exported)
            and existing_manifest.get("source", {}).get("sha256") == source_sha256
            and existing_manifest.get("output", {}).get("sha256") == _sha256(destination)
            and existing_manifest.get("ticker_mapping") == mapping_metadata
            and existing_manifest.get("target_exported") is False
        ):
            return BacktestSignalExport(
                signal_path=destination,
                manifest_path=manifest_path,
                start_date=start_date,
                end_date=end_date,
                row_count=int(len(exported)),
                symbol_count=int(exported["ticker"].nunique()),
            )
        raise FileExistsError(
            "Existing backtest signal artifacts do not match the current frozen OOS source; "
            "pass --force-export to replace them"
        )

    destination.parent.mkdir(parents=True, exist_ok=True)
    exported.to_parquet(destination, index=False)
    manifest = {
        "schema_version": 1,
        "source": {
            "path": str(source_path),
            "sha256": _sha256(source_path),
        },
        "output": {
            "path": str(destination),
            "sha256": _sha256(destination),
            "columns": ["date", "ticker", SIGNAL_COLUMN],
        },
        "signal_column": SIGNAL_COLUMN,
        "row_count": int(len(exported)),
        "symbol_count": int(exported["ticker"].nunique()),
        "start_date": start_date,
        "end_date": end_date,
        "ticker_mapping": mapping_metadata,
        "target_exported": False,
    }
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return BacktestSignalExport(
        signal_path=destination,
        manifest_path=manifest_path,
        start_date=start_date,
        end_date=end_date,
        row_count=int(len(exported)),
        symbol_count=int(exported["ticker"].nunique()),
    )


def resolve_backtest_entrypoint(backtest_root: str | Path | None = None) -> Path:
    if backtest_root is not None:
        roots = [Path(backtest_root).expanduser().resolve()]
    elif os.environ.get("FACTOR_BACKTEST_SKILL_ROOT"):
        roots = [Path(os.environ["FACTOR_BACKTEST_SKILL_ROOT"]).expanduser().resolve()]
    else:
        skill_root = Path(__file__).resolve().parents[2]
        roots = [
            skill_root.parent / BACKTEST_SKILL_DIRNAME,
            Path.home() / ".codex" / "skills" / BACKTEST_SKILL_DIRNAME,
        ]
    for root in roots:
        entrypoint = root / BACKTEST_ENTRYPOINT
        if entrypoint.is_file():
            return entrypoint
    checked = ", ".join(str(root / BACKTEST_ENTRYPOINT) for root in roots)
    raise FileNotFoundError(
        "Could not locate the external factor-backtest entrypoint. "
        f"Checked: {checked}. Provide --backtest-root or FACTOR_BACKTEST_SKILL_ROOT."
    )


def build_backtest_command(
    *,
    entrypoint: Path,
    signal_path: Path,
    data_root: Path,
    output_dir: Path,
    timespan: tuple[int, int],
    python_executable: str = sys.executable,
    strategy: str = "long_only_equal_weight",
    savemode: int = 3,
    init_cash: float = 1e8,
    overrides: Sequence[str] = (),
    reverse: bool = False,
    optimizer_root: Path | None = None,
    pure_alpha: bool = False,
    report: bool = False,
) -> list[str]:
    start_date, end_date = timespan
    if start_date > end_date:
        raise ValueError("Backtest timespan start must not be after end")
    command = [
        python_executable,
        str(entrypoint),
        "--input-file",
        str(signal_path),
        "--factor-column",
        SIGNAL_COLUMN,
        "--data-root",
        str(data_root),
        "--output-dir",
        str(output_dir),
        "--timespan",
        str(start_date),
        str(end_date),
        "--strategy",
        strategy,
        "--savemode",
        str(savemode),
        "--init-cash",
        str(init_cash),
    ]
    for override in overrides:
        if "=" not in override:
            raise ValueError(f"Backtest override must be key=value, got: {override}")
        command.extend(["--override", override])
    if reverse:
        command.append("--reverse")
    if optimizer_root is not None:
        command.extend(["--optimizer-root", str(optimizer_root)])
    if pure_alpha:
        command.append("--pure-alpha")
    if report:
        command.append("--report")
    return command


def _default_backtest_output(run_dir: Path) -> Path:
    root = run_dir / "backtest_results"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    candidate = root / f"run_{timestamp}"
    suffix = 1
    while candidate.exists():
        candidate = root / f"run_{timestamp}_{suffix:02d}"
        suffix += 1
    return candidate


def _resolve_timespan(
    exported: BacktestSignalExport,
    requested: Sequence[int] | None,
) -> tuple[int, int]:
    if requested is None:
        return exported.start_date, exported.end_date
    timespan = int(requested[0]), int(requested[1])
    if timespan[0] > timespan[1]:
        raise ValueError("Backtest timespan start must not be after end")
    if timespan[0] < exported.start_date or timespan[1] > exported.end_date:
        raise ValueError(
            "Requested timespan must remain inside the frozen OOS prediction interval "
            f"[{exported.start_date}, {exported.end_date}]"
        )
    return timespan


def build_factor_backtest_handoff(
    exported: BacktestSignalExport,
    *,
    timespan: tuple[int, int],
    reverse: bool = False,
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "handoff_skill": "factor-backtest",
        "input_file": str(exported.signal_path),
        "factor_column": SIGNAL_COLUMN,
        "timespan": [int(timespan[0]), int(timespan[1])],
        "signal_manifest": str(exported.manifest_path),
        "signal_direction": "lower_is_better" if reverse else "higher_is_better",
        "target_exported": False,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Export frozen OOS predictions for a Codex factor-backtest Skill handoff, "
            "or explicitly invoke a compatible external CLI."
        )
    )
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument(
        "--data-root",
        type=Path,
        help="Market-data root; required only for direct CLI execution.",
    )
    parser.add_argument("--backtest-root", type=Path)
    parser.add_argument("--ticker-map", type=Path, help="CSV/Parquet with symbol and ticker columns.")
    parser.add_argument("--signal-output", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--timespan", nargs=2, type=int, metavar=("START", "END"))
    parser.add_argument("--python-executable", default=sys.executable)
    parser.add_argument("--strategy", default="long_only_equal_weight")
    parser.add_argument("--savemode", type=int, default=3, choices=[0, 1, 2, 3])
    parser.add_argument("--init-cash", type=float, default=1e8)
    parser.add_argument("--override", action="append", default=[])
    parser.add_argument("--reverse", action="store_true")
    parser.add_argument("--optimizer-root", type=Path)
    parser.add_argument("--pure-alpha", action="store_true")
    parser.add_argument("--report", action="store_true")
    parser.add_argument("--force-export", action="store_true")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--export-only",
        action="store_true",
        help="Print a JSON handoff for the registered factor-backtest Skill and exit.",
    )
    mode.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and print the direct external CLI command without executing it.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        run_dir = args.run_dir.resolve()
        exported = export_backtest_signal(
            run_dir,
            output_path=args.signal_output,
            ticker_map_path=args.ticker_map,
            force=args.force_export,
        )
        timespan = _resolve_timespan(exported, args.timespan)
        handoff = build_factor_backtest_handoff(
            exported,
            timespan=timespan,
            reverse=args.reverse,
        )
        if args.export_only:
            print(json.dumps(handoff, ensure_ascii=False, indent=2), flush=True)
            return 0

        if args.data_root is None:
            raise ValueError("--data-root is required unless --export-only is used")
        entrypoint = resolve_backtest_entrypoint(args.backtest_root)
        data_root = args.data_root.resolve()
        if not data_root.is_dir():
            raise FileNotFoundError(f"Market data root does not exist: {data_root}")
        output_dir = (
            args.output_dir.resolve()
            if args.output_dir is not None
            else _default_backtest_output(run_dir)
        )
        command = build_backtest_command(
            entrypoint=entrypoint,
            signal_path=exported.signal_path,
            data_root=data_root,
            output_dir=output_dir,
            timespan=timespan,
            python_executable=args.python_executable,
            strategy=args.strategy,
            savemode=args.savemode,
            init_cash=args.init_cash,
            overrides=args.override,
            reverse=args.reverse,
            optimizer_root=args.optimizer_root.resolve() if args.optimizer_root else None,
            pure_alpha=args.pure_alpha,
            report=args.report,
        )
        print(shlex.join(command), flush=True)
        if args.dry_run:
            return 0
        completed = subprocess.run(command, check=False)
        if completed.returncode != 0:
            raise RuntimeError(f"External factor backtest failed with exit code {completed.returncode}")
        output_dir.mkdir(parents=True, exist_ok=True)
        invocation = {
            "schema_version": 1,
            "command": command,
            "signal_manifest": str(exported.manifest_path),
            "external_entrypoint": str(entrypoint),
            "output_dir": str(output_dir),
        }
        (output_dir / "selection_backtest_invocation.json").write_text(
            json.dumps(invocation, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return 0
    except (FileExistsError, FileNotFoundError, RuntimeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
