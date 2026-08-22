"""Write the minimal output contract for mRMR and SAGE runs."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from .config_utils import json_safe, write_json


def create_run_dir(cfg: Mapping[str, Any]) -> tuple[str, Path]:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    token = hashlib.sha1(f"{cfg['run_name']}:{stamp}".encode("utf-8")).hexdigest()[:8]
    run_id = f"{cfg['run_name']}_{stamp}_{token}"
    run_dir = Path(str(cfg["output_root"])) / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_id, run_dir


def _report_text(
    run_id: str,
    cfg: Mapping[str, Any],
    metadata: Mapping[str, Any],
    selected: Mapping[str, Any],
    warnings: list[str],
) -> str:
    factors = list(selected["selected_factors"])
    lines = [
        "# Factor Selection Report",
        "",
        f"- Run ID: `{run_id}`",
        f"- Mode: `{cfg['mode']}`",
        f"- Selection basis: `{selected['selection_basis']}`",
        f"- Input rows / dates / factors: {metadata['num_rows']} / {metadata['num_dates']} / {metadata['num_factors']}",
        f"- Selected factors: {len(factors)}",
        "",
        "## Selected Factors",
        "",
        ", ".join(f"`{factor}`" for factor in factors) if factors else "None",
        "",
        "## Boundaries",
        "",
        "- mRMR mode uses the local standard F-statistic/Pearson quotient implementation on training rows.",
        "- SAGE mode uses the local MarginalImputer and permutation estimator on a fixed model.",
        "- The validation period is not a locked trading holdout and no portfolio backtest is performed.",
    ]
    lines.extend(f"- {warning}" for warning in warnings)
    return "\n".join(lines) + "\n"


def write_artifacts(
    run_id: str,
    run_dir: Path,
    cfg: Mapping[str, Any],
    metadata: Mapping[str, Any],
    window: Any,
    warnings: list[str],
    frames: Mapping[str, pd.DataFrame],
    selected: Mapping[str, Any],
    method_metadata: Mapping[str, Any],
) -> dict[str, Any]:
    write_json(run_dir / "resolved_config.json", json_safe(cfg))
    write_json(
        run_dir / "input_manifest.json",
        {"data": metadata, "window": window.to_dict(), "warnings": warnings},
    )
    for name, frame in frames.items():
        frame.to_csv(run_dir / name, index=False)
    write_json(run_dir / "selected_factors.json", selected)
    if method_metadata:
        write_json(run_dir / "sage_metadata.json", method_metadata)
    (run_dir / "selection_report.md").write_text(
        _report_text(run_id, cfg, metadata, selected, warnings), encoding="utf-8"
    )
    algorithm_implementations = {
        "mrmr": "local-standard-v1",
        "sage": "local-marginal-mse-v1",
    }
    artifact_names = sorted(path.name for path in run_dir.iterdir() if path.is_file())
    manifest = {
        "run_id": run_id,
        "status": "completed",
        "mode": cfg["mode"],
        "num_selected_factors": len(selected["selected_factors"]),
        "algorithm_implementations": algorithm_implementations,
        "artifacts": artifact_names + ["run_manifest.json"],
    }
    write_json(run_dir / "run_manifest.json", manifest)
    return manifest
