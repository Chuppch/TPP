"""Command-line interface for safe CPU-only ILS-RC runs."""

from __future__ import annotations

import argparse
import sys

from .exact import exact_solve
from .io import format_result, format_solution, load_instance, result_as_json
from .domain.model import ILSConfig
from .core.ils_engine.ils import solve


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="CPU-only TPP ILS-RC reproduction")
    subparsers = parser.add_subparsers(dest="command", required=True)

    solve_parser = subparsers.add_parser("solve", help="run Algorithm 9 ILS-RC")
    solve_parser.add_argument("instance")
    solve_parser.add_argument("--k-max", type=int, default=100)
    solve_parser.add_argument("--lambda-max", type=int, default=20)
    solve_parser.add_argument("--delta-add", type=int, default=1)
    solve_parser.add_argument("--delta-drop", type=int, default=1)
    solve_parser.add_argument("--delta-exchange", type=int, default=1)
    solve_parser.add_argument("--alpha", type=float, default=0.2)
    solve_parser.add_argument("--seed", type=int, default=0)
    solve_parser.add_argument("--json", action="store_true", help="print JSON output")

    exact_parser = subparsers.add_parser(
        "exact", help="exhaustively solve an instance with at most eight markets"
    )
    exact_parser.add_argument("instance")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        instance = load_instance(args.instance)
        if args.command == "exact":
            print(format_solution(exact_solve(instance)))
            return 0

        config = ILSConfig(
            k_max=args.k_max,
            lambda_max=args.lambda_max,
            delta_add=args.delta_add,
            delta_drop=args.delta_drop,
            delta_exchange=args.delta_exchange,
            alpha=args.alpha,
            seed=args.seed,
        )
        result = solve(instance, config)
        print(result_as_json(result) if args.json else format_result(result))
        return 0
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
