"""Independent exhaustive oracle for instances with at most eight markets."""

from __future__ import annotations

from itertools import combinations, permutations

from .domain.evaluation import InfeasibleSolutionError, build_solution, choose_best
from .domain.model import MAX_EXACT_MARKETS, Solution, TPPInstance


def exact_solve(instance: TPPInstance) -> Solution:
    if instance.market_count > MAX_EXACT_MARKETS:
        raise ValueError(
            f"Exact validation is limited to {MAX_EXACT_MARKETS} markets; "
            f"received {instance.market_count}."
        )

    best: Solution | None = None
    for size in range(1, instance.market_count + 1):
        for subset in combinations(instance.markets, size):
            try:
                # Coverage and purchase cost depend only on the subset.
                build_solution(instance, (0, *subset, 0))
            except InfeasibleSolutionError:
                continue
            for order in permutations(subset):
                candidate = build_solution(instance, (0, *order, 0))
                if best is None:
                    best = candidate
                else:
                    best = choose_best((best, candidate))
    if best is None:
        raise ValueError("No feasible solution exists.")
    return best
