#!/usr/bin/env python3
"""Run deterministic ILS-RC experiments and write one raw CSV row per run."""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

try:
    from .experiment_common import (
        RAW_FIELDS,
        calculate_gap,
        discover_instance_files,
        encode_int_sequence,
        format_number,
        load_reference_costs,
        parse_seeds,
        write_csv_rows,
    )
except ImportError:  # Direct execution: python3 scripts/run_benchmarks.py
    from experiment_common import (  # type: ignore[no-redef]
        RAW_FIELDS,
        calculate_gap,
        discover_instance_files,
        encode_int_sequence,
        format_number,
        load_reference_costs,
        parse_seeds,
        write_csv_rows,
    )

from tpp.core.ils_engine.ils import solve  # noqa: E402
from tpp.domain.evaluation import assert_solution_consistent  # noqa: E402
from tpp.domain.model import ILSConfig, MAX_EXACT_MARKETS  # noqa: E402
from tpp.exact import exact_solve  # noqa: E402
from tpp.io import load_instance  # noqa: E402


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run single-process, CPU-only ILS-RC benchmark experiments."
    )
    parser.add_argument(
        "instances",
        nargs="+",
        help="JSON instance files or directories searched recursively for JSON files",
    )
    parser.add_argument("--output", default="tmp/experiments/raw_results.csv")
    parser.add_argument("--seeds", default="0,1,2,3,4")
    parser.add_argument("--known-best", help="CSV with instance,best_known_cost columns")
    parser.add_argument(
        "--exact-small",
        action="store_true",
        help="use the exhaustive oracle as reference when market_count <= 8",
    )
    parser.add_argument("--append", action="store_true", help="append rows to an existing CSV")
    parser.add_argument(
        "--max-runs",
        type=int,
        default=100,
        help="safety cap for instance count multiplied by seed count",
    )
    parser.add_argument("--k-max", type=int, default=100)
    parser.add_argument("--lambda-max", type=int, default=20)
    parser.add_argument("--delta-add", type=int, default=1)
    parser.add_argument("--delta-drop", type=int, default=1)
    parser.add_argument("--delta-exchange", type=int, default=1)
    parser.add_argument("--alpha", type=float, default=0.2)
    return parser


def _blank_record(
    *,
    name: str,
    source: Path,
    market_count: int,
    item_count: int,
    seed: int,
    config: ILSConfig,
) -> dict[str, object]:
    return {
        "instance": name,
        "source": str(source),
        "market_count": market_count,
        "item_count": item_count,
        "algorithm": "ils_rc_baseline",
        "seed": seed,
        "k_max": config.k_max,
        "lambda_max": config.lambda_max,
        "delta_add": config.delta_add,
        "delta_drop": config.delta_drop,
        "delta_exchange": config.delta_exchange,
        "alpha": format_number(config.alpha),
        "route": "",
        "item_markets": "",
        "travel_cost": "",
        "purchase_cost": "",
        "total_cost": "",
        "best_known_cost": "",
        "gap_percent": "",
        "feasible": "false",
        "iterations": "",
        "perturbations": "",
        "diversity_restarts": "",
        "elapsed_seconds": "",
        "error": "",
    }


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        sources = discover_instance_files(args.instances)
        seeds = parse_seeds(args.seeds)
        if args.max_runs <= 0:
            raise ValueError("max-runs must be greater than zero.")
        run_count = len(sources) * len(seeds)
        if run_count > args.max_runs:
            raise ValueError(
                f"Safety cap exceeded: {run_count} planned runs > {args.max_runs}. "
                "Narrow the inputs or explicitly raise --max-runs."
            )
        references = load_reference_costs(args.known_best)

        loaded = [(source, load_instance(source)) for source in sources]
        names = [instance.name for _source, instance in loaded]
        if len(set(names)) != len(names):
            raise ValueError("Instance names must be unique across one experiment batch.")

        rows: list[dict[str, object]] = []
        failures = 0
        for source, instance in loaded:
            reference = references.get(instance.name)
            reference_kind = "known-best" if reference is not None else "unavailable"
            if args.exact_small and instance.market_count <= MAX_EXACT_MARKETS:
                exact_cost = exact_solve(instance).total_cost
                if reference is not None and not math.isclose(
                    exact_cost, reference, rel_tol=0.0, abs_tol=1e-9
                ):
                    raise ValueError(
                        f"Known-best cost for {instance.name!r} is {reference:g}, "
                        f"but the exact oracle found {exact_cost:g}."
                    )
                reference = exact_cost
                reference_kind = "exact"

            print(
                f"instance={instance.name} markets={instance.market_count} "
                f"items={instance.item_count} reference={reference_kind}"
            )
            for seed in seeds:
                config = ILSConfig(
                    k_max=args.k_max,
                    lambda_max=args.lambda_max,
                    delta_add=args.delta_add,
                    delta_drop=args.delta_drop,
                    delta_exchange=args.delta_exchange,
                    alpha=args.alpha,
                    seed=seed,
                )
                row = _blank_record(
                    name=instance.name,
                    source=source,
                    market_count=instance.market_count,
                    item_count=instance.item_count,
                    seed=seed,
                    config=config,
                )
                try:
                    result = solve(instance, config)
                    assert_solution_consistent(instance, result.solution)
                    gap = calculate_gap(result.solution.total_cost, reference)
                    row.update(
                        {
                            "route": encode_int_sequence(result.solution.route),
                            "item_markets": encode_int_sequence(result.solution.item_markets),
                            "travel_cost": format_number(result.solution.travel_cost),
                            "purchase_cost": format_number(result.solution.purchase_cost),
                            "total_cost": format_number(result.solution.total_cost),
                            "best_known_cost": format_number(reference),
                            "gap_percent": format_number(gap),
                            "feasible": "true",
                            "iterations": result.iterations,
                            "perturbations": result.perturbations,
                            "diversity_restarts": result.diversity_restarts,
                            "elapsed_seconds": format_number(result.elapsed_seconds),
                        }
                    )
                    print(
                        f"  seed={seed} cost={result.solution.total_cost:g} "
                        f"gap={format_number(gap) or 'n/a'}% "
                        f"elapsed={result.elapsed_seconds:.6f}s"
                    )
                except (AssertionError, ValueError) as exc:
                    failures += 1
                    row["error"] = str(exc)
                    print(f"  seed={seed} status=FAIL error={exc}", file=sys.stderr)
                rows.append(row)

        write_csv_rows(args.output, RAW_FIELDS, rows, append=args.append)
        print(f"raw_results={Path(args.output)} runs={len(rows)} failures={failures}")
        return 1 if failures else 0
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
