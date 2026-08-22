from __future__ import annotations

import json
import multiprocessing as mp
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits

from .pool import ExhaustivePoolSelector
from .beam import BeamResidualSelector
from .cache import (
    cache_manifest_path,
    load_prepared_cache,
    write_cache_manifest,
    write_prepared_cache,
)
from .data import FactorStore, read_wide, select_universe, split_panel, stack_wide
from .lgbm_beam import LGBMBeamResidualSelector
from .metrics import prediction_metrics
from .preprocess import preprocess_label
from .ridge import fit_ridge
from .selector import PreparedFeatures, ResidualForwardSelector, SelectionResult
from .serialization import json_ready, write_json


@dataclass(frozen=True)
class ExperimentContext:
    universe: list[str]
    train_target: pd.Series
    valid_target: pd.Series
    oos_target: pd.Series
    selector: ResidualForwardSelector
    prepared: PreparedFeatures


_BEAM_WORKER_STATE: dict[str, object] = {}


def _prepare_targets(config: dict) -> tuple[list[str], pd.Series, pd.Series, pd.Series]:
    data_config = config["data"]
    split_config = config["split"]
    label_wide = read_wide(data_config["label_path"])
    universe = select_universe(
        label_wide,
        split_config["train_start"],
        split_config["train_end"],
        float(config["universe"]["train_label_min_coverage"]),
        config["universe"].get("symbols"),
    )
    label = preprocess_label(stack_wide(label_wide, universe), config["preprocess"])
    splits = split_panel(label, split_config, int(split_config["embargo_bars"]))
    return (
        universe,
        splits.train["value"].rename("target").dropna(),
        splits.valid["value"].rename("target").dropna(),
        splits.oos["value"].rename("target").dropna(),
    )


def _expected_cache_index(
    train_target: pd.Series,
    valid_target: pd.Series,
    oos_target: pd.Series,
) -> pd.MultiIndex:
    return train_target.index.append(valid_target.index).append(oos_target.index).sort_values()


def _configured_factor_names(data_config: dict) -> list[str] | None:
    factor_dir_value = data_config.get("factor_dir")
    if not factor_dir_value:
        return None
    factor_dir = Path(factor_dir_value)
    if not factor_dir.exists():
        return None
    names = sorted(path.stem for path in factor_dir.glob("*.parquet"))
    return names or None


def prepare_experiment(config: dict) -> ExperimentContext:
    data_config = config["data"]
    universe, train_target, valid_target, oos_target = _prepare_targets(config)
    expected_index = _expected_cache_index(train_target, valid_target, oos_target)
    cache_path_value = data_config.get("prepared_feature_cache")
    cache_path = Path(cache_path_value) if cache_path_value else None
    expected_factor_names = _configured_factor_names(data_config)
    if cache_path is not None and cache_path.exists():
        cached = load_prepared_cache(
            cache_path,
            expected_index,
            universe,
            config["preprocess"],
            config["split"],
            expected_factor_names,
        )
        store = FactorStore(data_config.get("factor_dir"), universe, factor_names=cached.columns)
        selector = ResidualForwardSelector(store, config["preprocess"], config["model"], config["selection"])
        prepared = PreparedFeatures(
            train=cached.loc[train_target.index],
            valid=cached.loc[valid_target.index],
            oos=cached.loc[oos_target.index],
        )
    else:
        store = FactorStore(data_config.get("factor_dir"), universe)
        selector = ResidualForwardSelector(store, config["preprocess"], config["model"], config["selection"])
        prepared = selector.prepare_features(train_target.index, valid_target.index, oos_target.index)
        if cache_path is not None:
            combined = pd.concat([prepared.train, prepared.valid, prepared.oos]).sort_index()
            write_prepared_cache(
                cache_path,
                combined,
                expected_index,
                universe,
                config["preprocess"],
                config["split"],
            )
    return ExperimentContext(universe, train_target, valid_target, oos_target, selector, prepared)


def validate_cache_experiment(config: dict, write_manifest: bool = False) -> Path:
    data_config = config["data"]
    cache_path_value = data_config.get("prepared_feature_cache")
    if not cache_path_value:
        raise ValueError("data.prepared_feature_cache is required")
    cache_path = Path(cache_path_value)
    if not cache_path.exists():
        raise FileNotFoundError(cache_path)
    universe, train_target, valid_target, oos_target = _prepare_targets(config)
    expected_index = _expected_cache_index(train_target, valid_target, oos_target)
    expected_factor_names = _configured_factor_names(data_config)
    if write_manifest:
        write_cache_manifest(
            cache_path,
            expected_index,
            universe,
            config["preprocess"],
            config["split"],
            expected_factor_names,
        )
    else:
        load_prepared_cache(
            cache_path,
            expected_index,
            universe,
            config["preprocess"],
            config["split"],
            expected_factor_names,
        )
    return cache_manifest_path(cache_path)


def _metric_value(row: pd.Series, name: str) -> float | None:
    return float(row[name]) if name in row else None


def _model_metadata(config: dict, model) -> dict:
    model_type = config["model"].get("type", "ridge")
    if model_type == "lgbm":
        return {
            "type": "lgbm",
            "iterations": int(model.iterations),
            "feature_importance": model.coefficients.to_dict(),
        }
    return {
        "type": "ridge",
        "alpha": float(model.alpha),
        "intercept": float(model.intercept),
        "coefficients": model.coefficients.to_dict(),
    }


def _write_selection_result(
    config: dict,
    context: ExperimentContext,
    result: SelectionResult,
    output_dir: Path,
    seed: int,
    initial_factor: str,
) -> dict:
    output_dir.mkdir(parents=True, exist_ok=False)
    result.history.to_csv(output_dir / "iteration_history.csv", index=False)
    beam_history = result.history.attrs.get("beam_history")
    if beam_history is not None:
        beam_history.to_csv(output_dir / "beam_history.csv", index=False)
    result.rankings.to_csv(output_dir / "residual_top10.csv", index=False)
    best_row = result.history.loc[result.history["is_best"]].iloc[-1]
    summary = {
        "schema_version": 2,
        "seed": seed,
        "initial_factor": initial_factor,
        "universe": context.universe,
        "universe_size": len(context.universe),
        "best_iteration": result.best_iteration,
        "selected_factors": result.selected_factors,
        "best_cv_score": _metric_value(best_row, "cv_score"),
        "best_cv_mean_ic": _metric_value(best_row, "cv_mean_ic"),
        "best_cv_std_ic": _metric_value(best_row, "cv_std_ic"),
        "best_cv_min_ic": _metric_value(best_row, "cv_min_ic"),
        "best_cv_se": _metric_value(best_row, "cv_se"),
        "best_valid_mean_ic": _metric_value(best_row, "valid_mean_ic"),
        "best_valid_icir": _metric_value(best_row, "valid_icir"),
        "model": _model_metadata(config, result.model),
        "oos_evaluation": "not_run",
    }
    for name in (
        "stopped_early",
        "searched_depth",
        "stale_depths",
        "candidate_evaluations",
        "searched_steps",
        "pool_capacity",
    ):
        if name in result.history.attrs:
            summary[name] = result.history.attrs[name]
    write_json(output_dir / "summary.json", summary)
    return json_ready(summary)


def _write_resolved_config(output_dir: Path, config: dict) -> None:
    write_json(output_dir / "config.json", config)


def _build_beam_selector(config: dict) -> BeamResidualSelector:
    model_type = config["model"].get("type", "ridge")
    if model_type == "lgbm":
        selector_class = LGBMBeamResidualSelector
    elif model_type == "ridge":
        selector_class = BeamResidualSelector
    else:
        raise ValueError(f"Unsupported model.type: {model_type}")
    return selector_class(
        config["preprocess"],
        config["model"],
        config["selection"],
        config["beam"],
        int(config["split"]["embargo_bars"]),
    )


def run_beam_experiment(config: dict) -> Path:
    context = prepare_experiment(config)
    development_target, development_features, development_prepared = _prepare_beam_data(context)
    seed = int(config["selection"]["random_seed"])
    configured_initial = config["selection"].get("initial_factor")
    if bool(config["beam"].get("deterministic_roots", False)):
        initial_factor = "deterministic_super_root"
    else:
        initial_factor = configured_initial or str(np.random.default_rng(seed).choice(context.selector.store.factor_names))
    result = _fit_beam(
        config, development_target, context.valid_target, development_features, development_prepared, initial_factor
    )
    root = Path(config["output"]["root"])
    run_name = f"{config['output']['experiment_name']}_beam_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    output_dir = root / run_name
    _write_selection_result(config, context, result, output_dir, seed, initial_factor)
    _write_resolved_config(output_dir, config)
    return output_dir


def run_pool_experiment(config: dict) -> Path:
    context = prepare_experiment(config)
    development_target, development_features, development_prepared = _prepare_beam_data(context)
    selector = ExhaustivePoolSelector(
        config["preprocess"],
        config["model"],
        config["selection"],
        config["beam"],
        config["pool"],
        int(config["split"]["embargo_bars"]),
    )
    result = selector.fit(development_target, context.valid_target, development_prepared)
    best_row = result.history.loc[result.history["is_best"]].iloc[-1]
    result.model = selector._fit(
        development_features,
        development_target,
        tuple(result.selected_factors),
        float(best_row["ridge_alpha"]),
    )
    root = Path(config["output"]["root"])
    run_name = f"{config['output']['experiment_name']}_pool_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    output_dir = root / run_name
    _write_selection_result(
        config,
        context,
        result,
        output_dir,
        int(config["selection"]["random_seed"]),
        "empty_pool",
    )
    _write_resolved_config(output_dir, config)
    return output_dir


def _prepare_beam_data(context: ExperimentContext) -> tuple[pd.Series, pd.DataFrame, PreparedFeatures]:
    development_target = pd.concat([context.train_target, context.valid_target]).sort_index()
    development_features = pd.concat([context.prepared.train, context.prepared.valid]).sort_index()
    development_prepared = PreparedFeatures(
        train=development_features,
        valid=context.prepared.valid,
        oos=context.prepared.oos,
    )
    return development_target, development_features, development_prepared


def _fit_beam(
    config: dict,
    development_target: pd.Series,
    valid_target: pd.Series,
    development_features: pd.DataFrame,
    development_prepared: PreparedFeatures,
    initial_factor: str,
    selector: BeamResidualSelector | None = None,
) -> SelectionResult:
    selector = selector or _build_beam_selector(config)
    result = selector.fit(development_target, valid_target, development_prepared, initial_factor)
    best_row = result.history.loc[result.history["is_best"]].iloc[-1]
    alpha_value = best_row.get("ridge_alpha")
    alpha = float(alpha_value) if alpha_value is not None and np.isfinite(alpha_value) else None
    result.model = selector._fit(
        development_features,
        development_target,
        tuple(result.selected_factors),
        alpha,
    )
    return result


def _run_beam_worker(task: tuple[int, int, str, str]) -> dict:
    run_number, seed, initial_factor, run_dir_text = task
    context = _BEAM_WORKER_STATE["context"]
    selector = _BEAM_WORKER_STATE["selector"]
    config = _BEAM_WORKER_STATE["config"]
    development_target = _BEAM_WORKER_STATE["development_target"]
    development_features = _BEAM_WORKER_STATE["development_features"]
    development_prepared = _BEAM_WORKER_STATE["development_prepared"]
    if not isinstance(context, ExperimentContext) or not isinstance(selector, BeamResidualSelector):
        raise RuntimeError("Beam worker state was not initialized")
    with threadpool_limits(limits=1):
        result = _fit_beam(
            config,
            development_target,
            context.valid_target,
            development_features,
            development_prepared,
            initial_factor,
            selector,
        )
    summary = _write_selection_result(config, context, result, Path(run_dir_text), seed, initial_factor)
    return {
        "run": run_number,
        "seed": seed,
        "initial_factor": initial_factor,
        "best_iteration": summary["best_iteration"],
        "best_valid_mean_ic": summary["best_valid_mean_ic"],
        "best_valid_icir": summary["best_valid_icir"],
        "selected_factors": json.dumps(summary["selected_factors"], ensure_ascii=False),
    }


def run_many_beam_experiments(config: dict, runs: int, master_seed: int, jobs: int = 1) -> Path:
    context = prepare_experiment(config)
    factor_names = context.selector.store.factor_names
    if runs < 1 or runs > len(factor_names):
        raise ValueError(f"runs must be between 1 and {len(factor_names)}")
    if runs > 1 and bool(config["beam"].get("deterministic_roots", False)):
        raise ValueError("run-many-beam requires beam.deterministic_roots=false when runs > 1")
    development_target, development_features, development_prepared = _prepare_beam_data(context)
    initial_factors = np.random.default_rng(master_seed).choice(factor_names, size=runs, replace=False).tolist()
    root = Path(config["output"]["root"])
    batch_name = f"{config['output']['experiment_name']}_beam_batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    batch_dir = root / batch_name
    batch_dir.mkdir(parents=True, exist_ok=False)
    jobs = min(max(1, int(jobs)), runs)
    selector = _build_beam_selector(config)
    selector._prepare_cv(development_prepared, development_target)
    _BEAM_WORKER_STATE.clear()
    _BEAM_WORKER_STATE.update(
        {
            "config": config,
            "context": context,
            "selector": selector,
            "development_target": development_target,
            "development_features": development_features,
            "development_prepared": development_prepared,
        }
    )
    tasks = [
        (
            run_number,
            master_seed + run_number - 1,
            initial_factor,
            str(batch_dir / f"run_{run_number:03d}_seed_{master_seed + run_number - 1}"),
        )
        for run_number, initial_factor in enumerate(initial_factors, start=1)
    ]
    summaries: list[dict] = []

    def record(summary: dict) -> None:
        summaries.append(summary)
        pd.DataFrame(summaries).sort_values("run").to_csv(batch_dir / "batch_summary.csv", index=False)
        print(
            f"run={summary['run']}/{runs} seed={summary['seed']} initial={summary['initial_factor']} "
            f"best_iteration={summary['best_iteration']} valid_ic={summary['best_valid_mean_ic']:.6f}",
            flush=True,
        )

    if jobs == 1:
        for task in tasks:
            record(_run_beam_worker(task))
    else:
        with mp.get_context("fork").Pool(processes=jobs) as pool:
            for summary in pool.imap_unordered(_run_beam_worker, tasks):
                record(summary)
    pd.DataFrame(summaries).sort_values("run").to_csv(batch_dir / "batch_summary.csv", index=False)
    write_batch_diagnostics(batch_dir)
    _write_resolved_config(batch_dir, config)
    return batch_dir


def run_experiment(config: dict) -> Path:
    context = prepare_experiment(config)
    seed = int(config["selection"]["random_seed"])
    configured_initial = config["selection"].get("initial_factor")
    initial_factor = configured_initial or str(np.random.default_rng(seed).choice(context.selector.store.factor_names))
    result = context.selector.fit(
        context.train_target,
        context.valid_target,
        prepared=context.prepared,
        random_seed=seed,
        initial_factor=initial_factor,
    )
    root = Path(config["output"]["root"])
    run_name = f"{config['output']['experiment_name']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    output_dir = root / run_name
    _write_selection_result(config, context, result, output_dir, seed, initial_factor)
    _write_resolved_config(output_dir, config)
    return output_dir


def run_many_experiments(config: dict, runs: int, master_seed: int) -> Path:
    context = prepare_experiment(config)
    factor_names = context.selector.store.factor_names
    if runs < 1 or runs > len(factor_names):
        raise ValueError(f"runs must be between 1 and {len(factor_names)}")
    rng = np.random.default_rng(master_seed)
    initial_factors = rng.choice(factor_names, size=runs, replace=False).tolist()
    seeds = [master_seed + offset for offset in range(runs)]
    root = Path(config["output"]["root"])
    batch_name = f"{config['output']['experiment_name']}_batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    batch_dir = root / batch_name
    batch_dir.mkdir(parents=True, exist_ok=False)
    summaries: list[dict] = []
    for run_number, (seed, initial_factor) in enumerate(zip(seeds, initial_factors), start=1):
        result = context.selector.fit(
            context.train_target,
            context.valid_target,
            prepared=context.prepared,
            random_seed=seed,
            initial_factor=initial_factor,
        )
        run_dir = batch_dir / f"run_{run_number:03d}_seed_{seed}"
        summary = _write_selection_result(config, context, result, run_dir, seed, initial_factor)
        summaries.append(
            {
                "run": run_number,
                "seed": seed,
                "initial_factor": initial_factor,
                "best_iteration": summary["best_iteration"],
                "best_valid_mean_ic": summary["best_valid_mean_ic"],
                "best_valid_icir": summary["best_valid_icir"],
                "selected_factors": json.dumps(summary["selected_factors"], ensure_ascii=False),
            }
        )
        print(
            f"run={run_number}/{runs} seed={seed} initial={initial_factor} "
            f"best_iteration={summary['best_iteration']} valid_ic={summary['best_valid_mean_ic']:.6f}",
            flush=True,
        )
    pd.DataFrame(summaries).to_csv(batch_dir / "batch_summary.csv", index=False)
    write_batch_diagnostics(batch_dir)
    _write_resolved_config(batch_dir, config)
    return batch_dir


def evaluate_oos_experiment(config: dict, run_dir: str | Path, force: bool = False) -> Path:
    run_path = Path(run_dir)
    summary_path = run_path / "summary.json"
    stored_config_path = run_path / "config.json"
    if not summary_path.exists() or not stored_config_path.exists():
        raise FileNotFoundError("run_dir must contain summary.json and config.json")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    stored_config = json.loads(stored_config_path.read_text(encoding="utf-8"))
    comparable_sections = (
        "data",
        "split",
        "universe",
        "preprocess",
        "model",
        "selection",
        "beam",
        "pool",
    )
    for section_name in comparable_sections:
        if json_ready(config.get(section_name)) != stored_config.get(section_name):
            raise ValueError(f"Evaluation config does not match the frozen run section: {section_name}")
    prediction_path = run_path / "oos_predictions.parquet"
    evaluation_path = run_path / "oos_evaluation.json"
    if not force and (prediction_path.exists() or evaluation_path.exists()):
        raise FileExistsError("OOS evaluation already exists; pass --force to replace it")

    context = prepare_experiment(config)
    selected_factors = [str(name) for name in summary["selected_factors"]]
    development_target, development_features, _ = _prepare_beam_data(context)
    selected_features = development_features.loc[:, selected_factors]
    model_type = config["model"].get("type", "ridge")
    if model_type == "lgbm":
        selector = _build_beam_selector(config)
        model = selector._fit(
            development_features,
            development_target,
            tuple(selected_factors),
            None,
        )
    else:
        model = fit_ridge(
            selected_features,
            development_target,
            alpha=float(summary["model"]["alpha"]),
            equal_date_weight=bool(config["model"]["equal_date_weight"]),
        )
    if context.prepared.oos is None:
        raise ValueError("OOS features were not prepared")
    oos_features = context.prepared.oos.loc[:, selected_factors]
    prediction = model.predict(oos_features)
    metrics = prediction_metrics(
        prediction,
        context.oos_target,
        method=config["selection"]["score_method"],
        min_count=int(config["preprocess"]["min_cross_section"]),
    )
    pd.DataFrame(
        {
            "target": context.oos_target,
            "prediction": prediction.reindex(context.oos_target.index),
        }
    ).to_parquet(prediction_path)
    write_json(
        evaluation_path,
        {
            "schema_version": 1,
            "selected_factors": selected_factors,
            "model": _model_metadata(config, model),
            "oos_metrics": metrics,
        },
    )
    return evaluation_path


def write_batch_diagnostics(batch_dir: str | Path) -> dict:
    batch_dir = Path(batch_dir)
    summary_frame = pd.read_csv(batch_dir / "batch_summary.csv")
    runs = len(summary_frame)
    factor_frequency: dict[str, int] = {}
    selected_sets: list[set[str]] = []
    for selected_factors in summary_frame["selected_factors"]:
        selected = set(json.loads(selected_factors))
        selected_sets.append(selected)
        for factor in selected:
            factor_frequency[factor] = factor_frequency.get(factor, 0) + 1
    pd.DataFrame(
        sorted(factor_frequency.items(), key=lambda item: (-item[1], item[0])),
        columns=["factor", "selection_count"],
    ).assign(selection_rate=lambda frame: frame["selection_count"] / runs).to_csv(
        batch_dir / "factor_frequency.csv", index=False
    )
    similarities: list[dict] = []
    for left in range(runs):
        for right in range(left + 1, runs):
            union = selected_sets[left] | selected_sets[right]
            similarities.append(
                {
                    "left_run": int(summary_frame.iloc[left]["run"]),
                    "right_run": int(summary_frame.iloc[right]["run"]),
                    "jaccard": len(selected_sets[left] & selected_sets[right]) / len(union),
                }
            )
    similarity_frame = pd.DataFrame(similarities, columns=["left_run", "right_run", "jaccard"])
    similarity_frame.to_csv(batch_dir / "path_similarity.csv", index=False)
    valid = summary_frame["best_valid_mean_ic"]
    continued = summary_frame["best_iteration"] > 1
    metrics = {
        "runs": runs,
        "valid_mean_ic": float(valid.mean()),
        "valid_median_ic": float(valid.median()),
        "valid_std_ic": float(valid.std(ddof=1)),
        "valid_q10_ic": float(valid.quantile(0.1)),
        "valid_q90_ic": float(valid.quantile(0.9)),
        "positive_valid_rate": float((valid > 0).mean()),
        "best_iteration_one_rate": float((~continued).mean()),
        "continued_path_valid_mean_ic": float(summary_frame.loc[continued, "best_valid_mean_ic"].mean()),
        "path_jaccard_mean": float(similarity_frame["jaccard"].mean()),
        "path_jaccard_median": float(similarity_frame["jaccard"].median()),
    }
    write_json(batch_dir / "batch_metrics.json", metrics)
    return json_ready(metrics)
