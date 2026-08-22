from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from .alpha101_formulas import compute_all_alpha101
from .alpha191_formulas import compute_all_alpha191
from .alpha_compute import build_alpha_output_frame, default_alpha_n_jobs
from .data import (
    build_matrices,
    convert_to_unadjusted_price,
    load_benchmark_matrices,
    load_market_data_frame,
)
from .selector import resolve_alpha_selection


def _json_default(value: Any) -> Any:
    if hasattr(value, "item"):
        return value.item()
    return str(value)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file_obj:
        json.dump(payload, file_obj, ensure_ascii=False, indent=2, default=_json_default)
        file_obj.write("\n")


def resolve_output_dir(config: dict[str, Any], *, skill_root: Path, cli_output: str | None) -> Path:
    raw = cli_output or str(config.get("output_dir", "outputs/alpha_compute_example")).strip()
    path = Path(raw).expanduser()
    if path.is_absolute():
        return path.resolve()
    if cli_output:
        return (Path.cwd() / path).resolve()
    return (skill_root / path).resolve()


def _compute_set(
    alpha_set: str,
    names: list[str],
    matrices: dict[str, pd.DataFrame],
    benchmark_matrices: dict[str, pd.DataFrame] | None,
    *,
    n_jobs: int,
    show_progress: bool,
) -> dict[str, pd.DataFrame]:
    if alpha_set == "alpha101":
        return compute_all_alpha101(matrices, names, n_jobs=n_jobs, show_progress=show_progress)
    if alpha_set == "alpha191":
        return compute_all_alpha191(matrices, benchmark_matrices, names, n_jobs=n_jobs, show_progress=show_progress)
    raise ValueError(f"Unsupported alpha set: {alpha_set}")


def run_alpha_compute(input_path: str | Path, *, output_dir: str | None = None) -> dict[str, Any]:
    input_path = Path(input_path).expanduser().resolve()
    if not input_path.is_file():
        raise FileNotFoundError(f"input JSON not found: {input_path}")

    skill_root = Path(__file__).resolve().parents[2]
    input_dir = input_path.parent

    with input_path.open("r", encoding="utf-8") as file_obj:
        config = json.load(file_obj)

    out_dir = resolve_output_dir(config, skill_root=skill_root, cli_output=output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    show_progress = bool(config.get("show_progress", True))
    n_jobs_raw = config.get("n_jobs", config.get("workers", None))
    n_jobs = default_alpha_n_jobs() if n_jobs_raw in (None, "") else int(n_jobs_raw)
    if n_jobs < 1:
        raise ValueError("n_jobs must be >= 1.")

    print(f"[Alpha Library] input file: {input_path}", flush=True)
    print(f"[Alpha Library] output directory: {out_dir}", flush=True)
    print("[Alpha Library] loading market data", flush=True)

    df_raw = load_market_data_frame(config, input_dir=input_dir, skill_root=skill_root)
    matrices = convert_to_unadjusted_price(build_matrices(df_raw))
    symbols = [str(symbol) for symbol in matrices["close"].columns]
    benchmark_matrices = load_benchmark_matrices(
        config,
        input_dir=input_dir,
        skill_root=skill_root,
        symbols=symbols,
    )
    selection = resolve_alpha_selection(config)

    print(
        "[Alpha Library] market data loaded: "
        f"rows={len(df_raw)} symbols={len(symbols)} dates={df_raw['date'].min()}..{df_raw['date'].max()}",
        flush=True,
    )

    output_files: dict[str, str] = {}
    skipped: list[dict[str, str]] = []
    computed_counts: dict[str, int] = {}
    requested_counts: dict[str, int] = {}
    nan_counts_by_set: dict[str, dict[str, int]] = {}

    for alpha_set, names in selection.items():
        requested_counts[alpha_set] = len(names)
        print(f"[Alpha Library] computing {alpha_set}: requested={len(names)} n_jobs={n_jobs}", flush=True)
        alpha_results = _compute_set(
            alpha_set,
            names,
            matrices,
            benchmark_matrices,
            n_jobs=n_jobs,
            show_progress=show_progress,
        )

        computed_names = sorted(alpha_results)
        missing_names = [name for name in names if name not in alpha_results]
        for name in missing_names:
            skipped.append({"alpha_set": alpha_set, "alpha_name": name, "reason": "returned_none"})

        if computed_names:
            result_df, nan_counts = build_alpha_output_frame(df_raw, alpha_results, alpha_order=computed_names)
            output_path = out_dir / f"{alpha_set}_values.csv"
            result_df.to_csv(output_path, index=False)
            output_files[f"{alpha_set}_values_path"] = str(output_path)
            computed_counts[alpha_set] = len(computed_names)
            nan_counts_by_set[alpha_set] = nan_counts
            print(f"[Alpha Library] {alpha_set} finished: computed={len(computed_names)} skipped={len(missing_names)}", flush=True)
        else:
            computed_counts[alpha_set] = 0
            nan_counts_by_set[alpha_set] = {}
            print(f"[Alpha Library] {alpha_set} finished: computed=0 skipped={len(missing_names)}", flush=True)

    summary_path = out_dir / "alpha_compute_summary.json"
    skipped_path = out_dir / "skipped_factors.json"
    run_config_path = out_dir / "run_config.json"
    summary = {
        "ok": True,
        "input_path": str(input_path),
        "output_dir": str(out_dir),
        "market_data_row_count": int(len(df_raw)),
        "symbol_count": int(len(symbols)),
        "date_range": [str(df_raw["date"].min()), str(df_raw["date"].max())],
        "alpha_sets": list(selection),
        "requested_counts": requested_counts,
        "computed_counts": computed_counts,
        "skipped_count": len(skipped),
        "output_files": output_files,
        "summary_path": str(summary_path),
        "skipped_factors_path": str(skipped_path),
        "run_config_path": str(run_config_path),
        "n_jobs": n_jobs,
    }

    write_json(summary_path, summary)
    write_json(skipped_path, skipped)
    write_json(run_config_path, config)

    summary["nan_counts"] = nan_counts_by_set
    return summary
