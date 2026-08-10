#!/usr/bin/env python3
"""Run, verify, summarize, and plot one small CPU-only experiment batch."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    from . import plot_results, run_benchmarks, summarize_results, verify_results
except ImportError:  # Direct execution
    import plot_results  # type: ignore[no-redef]
    import run_benchmarks  # type: ignore[no-redef]
    import summarize_results  # type: ignore[no-redef]
    import verify_results  # type: ignore[no-redef]


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Execute the complete TPP experiment pipeline.")
    parser.add_argument("instances", nargs="+", help="JSON files or directories")
    parser.add_argument("--output-dir", default="tmp/experiments")
    parser.add_argument("--seeds", default="0,1,2,3,4")
    parser.add_argument("--known-best")
    parser.add_argument("--exact-small", action="store_true")
    parser.add_argument("--max-runs", type=int, default=100)
    parser.add_argument("--k-max", type=int, default=100)
    parser.add_argument("--lambda-max", type=int, default=20)
    parser.add_argument("--delta-add", type=int, default=1)
    parser.add_argument("--delta-drop", type=int, default=1)
    parser.add_argument("--delta-exchange", type=int, default=1)
    parser.add_argument("--alpha", type=float, default=0.2)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    output_dir = Path(args.output_dir)
    raw = output_dir / "raw_results.csv"
    verification = output_dir / "verification.json"
    summary = output_dir / "summary.csv"
    algorithm_summary = output_dir / "algorithm_summary.csv"
    figures = output_dir / "figures"

    run_args = [
        *args.instances,
        "--output",
        str(raw),
        "--seeds",
        args.seeds,
        "--max-runs",
        str(args.max_runs),
        "--k-max",
        str(args.k_max),
        "--lambda-max",
        str(args.lambda_max),
        "--delta-add",
        str(args.delta_add),
        "--delta-drop",
        str(args.delta_drop),
        "--delta-exchange",
        str(args.delta_exchange),
        "--alpha",
        str(args.alpha),
    ]
    if args.known_best:
        run_args.extend(("--known-best", args.known_best))
    if args.exact_small:
        run_args.append("--exact-small")

    print("stage=run")
    status = run_benchmarks.main(run_args)
    if status != 0:
        return status
    print("stage=verify")
    status = verify_results.main([str(raw), "--report", str(verification)])
    if status != 0:
        return status
    print("stage=summarize")
    status = summarize_results.main(
        [
            str(raw),
            "--output",
            str(summary),
            "--algorithm-output",
            str(algorithm_summary),
        ]
    )
    if status != 0:
        return status
    print("stage=plot")
    status = plot_results.main([str(raw), "--output-dir", str(figures)])
    if status != 0:
        return status
    print(f"pipeline_status=PASS output_dir={output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
