#!/usr/bin/env python3
"""Run the paper example and tiny exhaustive checks on one CPU process."""

from __future__ import annotations

import random
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tpp.core.ils_engine.ils import solve  # noqa: E402
from tpp.domain.evaluation import assert_solution_consistent  # noqa: E402
from tpp.domain.model import ILSConfig, TPPInstance  # noqa: E402
from tpp.exact import exact_solve  # noqa: E402
from tpp.io import load_instance  # noqa: E402


def make_random_instance(seed: int, symmetric: bool) -> TPPInstance:
    rng = random.Random(seed)
    market_count = 5
    item_count = 4
    node_count = market_count + 1
    travel = [[0.0 for _ in range(node_count)] for _ in range(node_count)]
    if symmetric:
        for left in range(node_count):
            for right in range(left + 1, node_count):
                cost = float(rng.randint(5, 40))
                travel[left][right] = cost
                travel[right][left] = cost
    else:
        for start in range(node_count):
            for end in range(node_count):
                if start != end:
                    travel[start][end] = float(rng.randint(5, 40))

    prices = [
        [float(rng.randint(10, 60)) if rng.random() < 0.6 else None for _ in range(item_count)]
        for _ in range(market_count)
    ]
    for item in range(item_count):
        if not any(row[item] is not None for row in prices):
            prices[rng.randrange(market_count)][item] = float(rng.randint(10, 60))
    kind = "symmetric" if symmetric else "asymmetric"
    return TPPInstance.from_market_matrices(f"tiny-{kind}-{seed}", travel, prices)


def verify(instance: TPPInstance, seed: int) -> tuple[float, float, float, float]:
    exact_started = time.perf_counter()
    optimum = exact_solve(instance)
    exact_seconds = time.perf_counter() - exact_started

    result = solve(
        instance,
        ILSConfig(k_max=40, lambda_max=8, alpha=0.4, seed=seed),
    )
    assert_solution_consistent(instance, result.solution)
    if result.solution.total_cost + 1e-9 < optimum.total_cost:
        raise AssertionError("Heuristic cost is lower than the exhaustive optimum.")
    gap = 100.0 * (result.solution.total_cost - optimum.total_cost) / optimum.total_cost
    return optimum.total_cost, result.solution.total_cost, gap, exact_seconds + result.elapsed_seconds


def main() -> int:
    print("CPU-only verification: one process, markets <= 5, exact limit <= 8")
    paper = load_instance(ROOT / "examples" / "paper_four_market.json")
    optimum, heuristic, gap, elapsed = verify(paper, seed=0)
    print(
        f"paper-four-market: exact={optimum:g}, ils={heuristic:g}, "
        f"gap={gap:.3f}%, elapsed={elapsed:.6f}s"
    )

    for seed, symmetric in ((7, True), (13, False), (29, True)):
        instance = make_random_instance(seed, symmetric)
        optimum, heuristic, gap, elapsed = verify(instance, seed)
        print(
            f"{instance.name}: exact={optimum:g}, ils={heuristic:g}, "
            f"gap={gap:.3f}%, elapsed={elapsed:.6f}s"
        )
    print("verification_status: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
