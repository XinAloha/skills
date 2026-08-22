from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import pytest

from residual_factor_selection.backtest_adapter import (
    build_backtest_command,
    build_factor_backtest_handoff,
    main as backtest_main,
    export_backtest_signal,
    resolve_backtest_entrypoint,
)


def _frozen_run(tmp_path: Path, symbols: list[str] | None = None) -> Path:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    for name in ["summary.json", "config.json", "oos_evaluation.json"]:
        (run_dir / name).write_text("{}\n", encoding="utf-8")
    dates = pd.to_datetime(["2024-01-02", "2024-01-03"])
    symbols = symbols or ["000001", "600000"]
    index = pd.MultiIndex.from_product([dates, symbols], names=["datetime", "symbol"])
    pd.DataFrame(
        {
            "target": [0.01, -0.02, 0.03, -0.04],
            "prediction": [0.4, -0.3, 0.2, -0.1],
        },
        index=index,
    ).to_parquet(run_dir / "oos_predictions.parquet")
    return run_dir


def test_export_backtest_signal_uses_only_frozen_predictions(tmp_path: Path) -> None:
    run_dir = _frozen_run(tmp_path)
    result = export_backtest_signal(run_dir)

    exported = pd.read_parquet(result.signal_path)
    assert exported.columns.tolist() == ["date", "ticker", "prediction"]
    assert exported["date"].tolist() == [20240102, 20240102, 20240103, 20240103]
    assert exported["ticker"].tolist() == [1, 600000, 1, 600000]
    assert result.start_date == 20240102
    assert result.end_date == 20240103
    assert result.row_count == 4
    assert result.symbol_count == 2

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["target_exported"] is False
    assert manifest["output"]["columns"] == ["date", "ticker", "prediction"]
    assert manifest["ticker_mapping"] == {"mode": "direct_integer"}
    reused = export_backtest_signal(run_dir)
    assert reused.signal_path == result.signal_path
    assert reused.manifest_path == result.manifest_path


def test_export_parses_integer_dates_and_requires_parquet_output(tmp_path: Path) -> None:
    run_dir = _frozen_run(tmp_path)
    frame = pd.read_parquet(run_dir / "oos_predictions.parquet").reset_index()
    frame["datetime"] = frame["datetime"].dt.strftime("%Y%m%d").astype("int64")
    frame.set_index(["datetime", "symbol"]).to_parquet(run_dir / "oos_predictions.parquet")

    result = export_backtest_signal(run_dir)
    exported = pd.read_parquet(result.signal_path)
    assert exported["date"].tolist() == [20240102, 20240102, 20240103, 20240103]

    with pytest.raises(ValueError, match="Parquet suffix"):
        export_backtest_signal(run_dir, output_path=tmp_path / "prediction.csv")


def test_export_requires_mapping_for_non_integer_symbols(tmp_path: Path) -> None:
    run_dir = _frozen_run(tmp_path, ["000001.SZ", "600000.SH"])
    with pytest.raises(ValueError, match="--ticker-map"):
        export_backtest_signal(run_dir)

    mapping_path = tmp_path / "ticker_map.csv"
    pd.DataFrame(
        {
            "symbol": ["000001.SZ", "600000.SH"],
            "ticker": [1, 600000],
        }
    ).to_csv(mapping_path, index=False)
    result = export_backtest_signal(run_dir, ticker_map_path=mapping_path)
    exported = pd.read_parquet(result.signal_path)
    assert exported["ticker"].tolist() == [1, 600000, 1, 600000]
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["ticker_mapping"]["mode"] == "mapping_file"


def test_export_rejects_non_finite_predictions_and_incomplete_runs(tmp_path: Path) -> None:
    run_dir = _frozen_run(tmp_path)
    frame = pd.read_parquet(run_dir / "oos_predictions.parquet")
    frame.iloc[0, frame.columns.get_loc("prediction")] = float("nan")
    frame.to_parquet(run_dir / "oos_predictions.parquet")
    with pytest.raises(ValueError, match="non-finite"):
        export_backtest_signal(run_dir)

    incomplete = tmp_path / "incomplete"
    incomplete.mkdir()
    with pytest.raises(FileNotFoundError, match="completed frozen OOS"):
        export_backtest_signal(incomplete)


def test_build_backtest_command_uses_public_cli_contract(tmp_path: Path) -> None:
    command = build_backtest_command(
        entrypoint=tmp_path / "backtest" / "scripts" / "run_factor_backtest.py",
        signal_path=tmp_path / "prediction.parquet",
        data_root=tmp_path / "market",
        output_dir=tmp_path / "output",
        timespan=(20240102, 20240131),
        python_executable="python",
        overrides=["longx=100", "benchmark=hs300"],
        reverse=True,
        report=True,
    )
    assert command[:2] == [
        "python",
        str(tmp_path / "backtest" / "scripts" / "run_factor_backtest.py"),
    ]
    assert command[command.index("--factor-column") + 1] == "prediction"
    assert command[command.index("--timespan") + 1 : command.index("--timespan") + 3] == [
        "20240102",
        "20240131",
    ]
    assert command.count("--override") == 2
    assert "--reverse" in command
    assert "--report" in command
    assert "target" not in command


def test_resolve_backtest_entrypoint_accepts_explicit_external_root(tmp_path: Path) -> None:
    root = tmp_path / "skill-factor-backtest"
    entrypoint = root / "scripts" / "run_factor_backtest.py"
    entrypoint.parent.mkdir(parents=True)
    entrypoint.write_text("print('ok')\n", encoding="utf-8")
    assert resolve_backtest_entrypoint(root) == entrypoint


def test_build_factor_backtest_handoff_is_explicit(tmp_path: Path) -> None:
    exported = export_backtest_signal(_frozen_run(tmp_path))
    handoff = build_factor_backtest_handoff(
        exported,
        timespan=(20240102, 20240103),
        reverse=True,
    )

    assert handoff == {
        "schema_version": 1,
        "handoff_skill": "factor-backtest",
        "input_file": str(exported.signal_path),
        "factor_column": "prediction",
        "timespan": [20240102, 20240103],
        "signal_manifest": str(exported.manifest_path),
        "signal_direction": "lower_is_better",
        "target_exported": False,
    }


def test_cli_export_only_emits_handoff_without_external_runtime(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    run_dir = _frozen_run(tmp_path)

    def fail_if_called(*args: object, **kwargs: object) -> None:
        raise AssertionError("export-only must not start an external process")

    monkeypatch.setattr("residual_factor_selection.backtest_adapter.subprocess.run", fail_if_called)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_selection_backtest.py",
            "--run-dir",
            str(run_dir),
            "--export-only",
        ],
    )

    assert backtest_main() == 0
    handoff = json.loads(capsys.readouterr().out)
    assert handoff["handoff_skill"] == "factor-backtest"
    assert handoff["factor_column"] == "prediction"
    assert handoff["timespan"] == [20240102, 20240103]
    assert handoff["signal_direction"] == "higher_is_better"
    assert handoff["target_exported"] is False
    assert Path(handoff["input_file"]).is_file()
    assert Path(handoff["signal_manifest"]).is_file()


def test_cli_direct_mode_requires_data_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    run_dir = _frozen_run(tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        ["run_selection_backtest.py", "--run-dir", str(run_dir)],
    )

    assert backtest_main() == 2
    assert "--data-root is required unless --export-only is used" in capsys.readouterr().err


def test_cli_dry_run_exports_and_reuses_signal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    run_dir = _frozen_run(tmp_path)
    data_root = tmp_path / "market"
    data_root.mkdir()
    backtest_root = tmp_path / "skill-factor-backtest"
    entrypoint = backtest_root / "scripts" / "run_factor_backtest.py"
    entrypoint.parent.mkdir(parents=True)
    entrypoint.write_text("raise SystemExit('dry-run only')\n", encoding="utf-8")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_selection_backtest.py",
            "--run-dir",
            str(run_dir),
            "--data-root",
            str(data_root),
            "--backtest-root",
            str(backtest_root),
            "--dry-run",
        ],
    )

    assert backtest_main() == 0
    assert backtest_main() == 0
    output = capsys.readouterr().out
    assert output.count("--factor-column prediction") == 2
    assert (run_dir / "backtest_input" / "prediction.parquet").exists()
