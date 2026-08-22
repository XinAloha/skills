from __future__ import annotations

import argparse

from .config import load_config, validate_config
from .experiment import (
    evaluate_oos_experiment,
    run_pool_experiment,
    run_beam_experiment,
    run_experiment,
    run_many_beam_experiments,
    run_many_experiments,
    validate_cache_experiment,
)
from .materialize import materialize_factorbank


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Residual-guided factor selection experiment tools")
    parser.add_argument("--config", default="config.yaml")
    subparsers = parser.add_subparsers(dest="command", required=True)

    materialize = subparsers.add_parser("materialize", help="Materialize factor libraries on panda bars")
    materialize.add_argument("--force", action="store_true")
    materialize.add_argument("--factor", action="append", dest="factors")
    materialize.add_argument("--symbol", action="append", dest="symbols")
    materialize.add_argument(
        "--library",
        action="append",
        choices=["alpha101", "alpha158", "alpha191"],
        dest="libraries",
    )
    materialize.add_argument("--jobs", type=int, default=1)

    subparsers.add_parser("run", help="Run one residual forward-selection path")
    subparsers.add_parser("run-beam", help="Run CV-pruned beam search")
    subparsers.add_parser("run-pool", help="Run exhaustive joint-CV factor-pool selection")
    run_many = subparsers.add_parser("run-many", help="Run multiple paths with shared prepared features")
    run_many.add_argument("--runs", type=int, default=20)
    run_many.add_argument("--master-seed", type=int)
    run_many_beam = subparsers.add_parser("run-many-beam", help="Run multiple beam paths with shared features")
    run_many_beam.add_argument("--runs", type=int, default=5)
    run_many_beam.add_argument("--master-seed", type=int)
    run_many_beam.add_argument("--jobs", type=int, default=8)

    evaluate = subparsers.add_parser("evaluate-oos", help="Evaluate one frozen run on OOS")
    evaluate.add_argument("--run-dir", type=str, required=True)
    evaluate.add_argument("--force", action="store_true")

    validate_cache = subparsers.add_parser("validate-cache", help="Validate a prepared-feature cache")
    validate_cache.add_argument("--write-manifest", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    config = load_config(args.config)
    validate_config(config, args.command)
    if args.command == "materialize":
        manifest = materialize_factorbank(
            config=config,
            libraries=args.libraries or ["alpha101", "alpha158", "alpha191"],
            factor_names=args.factors,
            symbols=args.symbols,
            force=args.force,
            n_jobs=args.jobs,
        )
        print(f"materialized={len(manifest)} manifest={config['data']['factor_manifest']}")
        return 0
    if args.command == "validate-cache":
        output_path = validate_cache_experiment(config, args.write_manifest)
        print(output_path)
        return 0
    if args.command == "evaluate-oos":
        output_path = evaluate_oos_experiment(config, args.run_dir, args.force)
        print(output_path)
        return 0
    if args.command in {"run-many", "run-many-beam"}:
        master_seed = (
            args.master_seed
            if args.master_seed is not None
            else int(config["selection"]["random_seed"])
        )
        if args.command == "run-many-beam":
            output_dir = run_many_beam_experiments(config, args.runs, master_seed, args.jobs)
        else:
            output_dir = run_many_experiments(config, args.runs, master_seed)
    elif args.command == "run-beam":
        output_dir = run_beam_experiment(config)
    elif args.command == "run-pool":
        output_dir = run_pool_experiment(config)
    else:
        output_dir = run_experiment(config)
    print(output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
